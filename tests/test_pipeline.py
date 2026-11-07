import csv
import json

import pytest
from pyspark.sql import types as T

from vitalflow import acquisition
from vitalflow.acquisition import acquire
from vitalflow.artifacts import staged_result
from vitalflow.config import VitalFlowError
from vitalflow.integration import METADATA_SCHEMA, verify_metadata
from vitalflow.pipeline import CONTROLLED, RunOptions, run
from vitalflow.quality import audit, classify_rows, clean_rows
from vitalflow.spark import REPLAY_COLUMNS, csv_strings


def read_json(path):
    return json.loads(path.read_text())


def test_controlled_quality_reports_and_selects_repeatable_row(spark, project):
    scenario = project.root / "data" / "scenarios" / "controlled_quality.csv"
    raw = csv_strings(spark, [scenario], REPLAY_COLUMNS)
    typed = classify_rows(raw)
    cleaned = clean_rows(typed)
    rows = cleaned.orderBy("time_s").collect()
    assert [(row.time_s, row.hr, row.pulse, row.resp, row.spo2) for row in rows] == [
        (0.0, 72.0, 71.0, 17.0, 98.0),
        (1.0, None, None, None, None),
        (2.0, 75.0, 73.0, None, None),
    ]
    result = audit(raw, typed, cleaned, provenance=CONTROLLED)
    assert result["before"]["rows"] == 8
    assert result["before"]["exact_duplicate_source_rows_beyond_first"] == 1
    assert result["before"]["repeated_valid_keys"] == {
        "groups": 1,
        "conflicting_groups": 1,
        "excess_rows": 3,
    }
    assert result["after"]["rows"] == 3
    assert result["after"]["duplicate_key_rows"] == 0
    assert result["actions"]["invalid_time_rows_dropped"] == 2
    assert result["actions"]["imputed_cells"] == 0
    fields = result["before"]["field_status_counts"]
    assert [
        fields[m][reason]
        for m, reason in [
            ("hr", "nan"),
            ("pulse", "malformed"),
            ("resp", "nonfinite"),
            ("spo2", "out_of_range"),
        ]
    ] == [1, 1, 1, 1]


def test_metadata_rejects_duplicates_and_missing_keys(spark):
    raw = spark.createDataFrame([("bidmc_01",), ("bidmc_02",)], "recording_id string")
    row = ("bidmc_01", "micu", 125.0, 1.0, ["HR", "PULSE", "RESP", "SpO2"], "1.0.0", "source")
    metadata = spark.createDataFrame([row, row, ("bidmc_03", *row[1:])], METADATA_SCHEMA)
    with pytest.raises(VitalFlowError, match=r"duplicate_metadata_ids.*bidmc_01") as exc:
        verify_metadata(raw, metadata, ["bidmc_01", "bidmc_02"])
    assert "'source_ids_without_metadata': ['bidmc_02']" in str(exc.value)
    assert "'metadata_ids_without_source': ['bidmc_03']" in str(exc.value)


def test_three_record_offline_smoke_parquet_and_repeat_run(spark, project, responses, monkeypatch):
    def mock_download(url, validate):
        data = responses[url]
        validate(data)
        return data

    monkeypatch.setattr(acquisition, "fetch", mock_download)
    records, _ = acquire(project, 3, offline=False)
    monkeypatch.setattr(acquisition, "fetch", lambda *_: pytest.fail("unexpected network request"))
    raw_files = [p for r in records for p in (r.numerics, r.fix)]
    raw_identity = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in raw_files}
    result = run(spark, project, RunOptions(3, replay_interval_s=0.02))
    snapshot = project.result(3)
    assert result["source_rows"] == 7
    assert result["invalid_time_rows_dropped"] == 1
    assert result["joined_rows"] == result["parquet_readback_rows"] == 6
    assert result["summary_groups"] == 3
    parquet = spark.read.parquet((snapshot / "data/processed/observations.parquet").as_uri())
    for field in ("time_s", "hr", "pulse", "resp", "spo2"):
        assert isinstance(parquet.schema[field].dataType, T.DoubleType)
    values = parquet.where("recording_id = 'bidmc_03' AND time_s = 240").first()
    assert (values.hr, values.pulse, values.resp, values.spo2, values.location) == (
        91.0,
        90.0,
        21.0,
        95.0,
        "micu",
    )
    missing = parquet.where("recording_id = 'bidmc_01' AND time_s = 1").first()
    assert missing.pulse is None and missing.spo2 is None
    provenance = read_json(snapshot / "provenance.json")
    assert all(item["status"] == "cached" for item in provenance["files"])
    velocity = read_json(snapshot / "benchmarks/velocity.json")
    assert velocity["total_processed_rows"] == 7
    assert velocity["total_valid_time_rows"] == 6
    assert len(velocity["batches"]) == 4
    assert velocity["batches"][0]["arrival_interval_ms"] is None
    for batch in velocity["batches"]:
        assert batch["arrival_to_completion_ms"] == pytest.approx(
            batch["queue_wait_ms"] + batch["spark_ingest_and_process_ms"], abs=0.002
        )
    volume = read_json(snapshot / "benchmarks/volume.json")
    assert volume["output_groups"] == {"aggregation": 3, "join_and_window": 5}
    assert "Join" in (snapshot / "benchmarks/join_and_window_plan.txt").read_text()
    with (snapshot / "analytics/by_recording.csv").open(newline="") as stream:
        summary = list(csv.DictReader(stream))
    assert summary[0]["pulse_completeness"] == "0.5"
    assert summary[0]["hr_mean"] == "71.0"

    stable = (
        "source_schema.json",
        "integration.json",
        "quality/source.json",
        "analytics/by_recording.csv",
        "analytics/by_minute.csv",
        "data/metadata/recordings.jsonl",
    )
    before = {name: (snapshot / name).read_bytes() for name in stable}
    repeated = run(spark, project, RunOptions(3, replay_interval_s=0.02))
    assert repeated["parquet_readback_rows"] == 6
    assert {name: (snapshot / name).read_bytes() for name in stable} == before
    assert {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in raw_files} == raw_identity


def test_snapshot_preserves_unmanaged_paths_and_previous_run_on_failure(project):
    from vitalflow.artifacts import RUN_FORMAT, write_json

    destination = project.result(3)
    destination.mkdir(parents=True)
    user_file = destination / "notes.txt"
    user_file.write_text("keep")
    with pytest.raises(VitalFlowError, match="unmanaged"):
        with staged_result(project, 3):
            pytest.fail("unmanaged folder must not be staged")
    assert user_file.read_text() == "keep"
    write_json(destination / "run.json", {"format": RUN_FORMAT, "recording_count": 3})
    with pytest.raises(ValueError, match="simulated"):
        with staged_result(project, 3) as stage:
            (stage / "partial.csv").write_text("incomplete")
            raise ValueError("simulated stage failure")
    assert not (destination / "partial.csv").exists()
    assert user_file.read_text() == "keep"
