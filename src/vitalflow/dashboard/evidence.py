"""Validate and reconcile generated evidence without importing Spark."""

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

import pandas as pd
import pyarrow.dataset as ds

from vitalflow.artifacts import RUN_FORMAT
from vitalflow.config import (
    DATASET_PAGE,
    DATASET_VERSION,
    MODES,
    SOURCE_BASE,
    Project,
    recording_ids,
)
from vitalflow.source import MEASURES, NUMERIC_FIELDS

RUN = "run.json"
PROVENANCE = "provenance.json"
SCHEMA = "source_schema.json"
INTEGRATION = "integration.json"
METADATA = "data/metadata/recordings.jsonl"
PARQUET = "data/processed/observations.parquet"
QUALITY = "quality/source.json"
FIXTURE = "quality/controlled_fixture.json"
COVERAGE = "quality/time_coverage.csv"
RECORDINGS = "analytics/by_recording.csv"
WINDOWS = "analytics/by_minute.csv"
VOLUME = "benchmarks/volume.json"
VELOCITY = "benchmarks/velocity.json"
PLANS = {
    "aggregation": "benchmarks/aggregation_plan.txt",
    "join_and_window": "benchmarks/join_and_window_plan.txt",
}
REQUIRED = (
    RUN,
    PROVENANCE,
    SCHEMA,
    INTEGRATION,
    METADATA,
    QUALITY,
    FIXTURE,
    COVERAGE,
    RECORDINGS,
    WINDOWS,
    VOLUME,
    VELOCITY,
)
SOURCE_KIND = "physionet_bidmc_original"
FIXTURE_KIND = "synthetic_controlled_fixture_not_physionet"
OPERATIONS = tuple(PLANS)
KEY_CHECKS = (
    "duplicate_metadata_ids",
    "metadata_ids_without_source",
    "missing_source_ids",
    "source_ids_without_metadata",
    "unexpected_source_ids",
)
METADATA_FIELDS = (
    "recording_id",
    "location",
    "numerics_sampling_hz",
    "signals_sampling_hz",
    "numeric_channels",
    "dataset_version",
    "source_fix_url",
)
Revision = tuple[tuple[str, int, int, int], ...]
Object = dict[str, Any]


class EvidenceError(ValueError):
    """An artifact is absent or fails the evidence contract."""

    def __init__(self, artifact: str, reason: str):
        self.artifact = artifact
        self.reason = reason
        super().__init__(f"{artifact}: {reason}")


def require(condition: Any, artifact: str, reason: str) -> None:
    if not condition:
        raise EvidenceError(artifact, reason)


def integer(value: Any, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def number(value: Any, minimum: float = 0) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= minimum


def stamp(value: Any) -> datetime:
    result = datetime.fromisoformat(value)
    if result.utcoffset() is None:
        raise ValueError("missing timezone")
    return result


def fields(value: Any, keys: tuple[str, ...], file: str) -> Object:
    require(isinstance(value, dict), file, "struktur objek tidak sesuai")
    missing = set(keys) - value.keys()
    require(not missing, file, f"field wajib tidak ada: {', '.join(sorted(missing))}")
    return value


def list_field(value: Any, file: str, *, nonempty: bool = False) -> list:
    require(isinstance(value, list) and (value or not nonempty), file, "daftar tidak sesuai")
    return value


def counts(value: Any, keys: tuple[str, ...], file: str) -> Object:
    result = fields(value, keys, file)
    require(all(integer(result[key]) for key in keys), file, "jumlah harus berupa bilangan bulat")
    return result


def read_object(root: Path, name: str) -> Object:
    try:
        return fields(json.loads((root / name).read_text(encoding="utf-8")), (), name)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(name, "berkas tidak dapat dibaca sebagai JSON") from exc


def read_csv(root: Path, name: str, required: tuple[str, ...]) -> pd.DataFrame:
    try:
        frame = pd.read_csv(root / name, dtype={"recording_id": str, "location": str})
    except (OSError, UnicodeError, ValueError) as exc:
        raise EvidenceError(name, "CSV kosong atau tidak dapat dibaca") from exc
    missing = set(required) - set(frame.columns)
    require(not missing, name, f"kolom wajib tidak ada: {', '.join(sorted(missing))}")
    require(not frame.empty, name, "CSV tidak memuat baris data")
    return frame.loc[:, list(required)].copy()


@dataclass(frozen=True)
class Metrics:
    recordings: int
    source_rows: int
    retained: int
    missing: int
    expected_cells: int
    median_arrival_ms: float
    median_processing_ms: float

    @property
    def completeness(self) -> float:
        return (self.expected_cells - self.missing) / self.expected_cells


@dataclass
class Snapshot:
    mode: str
    revision: Revision
    run: Object
    provenance: Object
    profiles: list[Object]
    integration: Object
    metadata: dict[str, Object]
    quality: Object
    fixture: Object
    coverage: pd.DataFrame
    recordings: pd.DataFrame
    windows: pd.DataFrame
    volume: Object
    velocity: Object
    metrics: Metrics

    @property
    def ids(self) -> list[str]:
        return self.run["recording_ids"]

    @property
    def folder(self) -> str:
        return f"outputs/{MODES[self.mode]:02d}-recordings"

    def report(self, scenario: str) -> Object:
        if scenario == "source":
            return self.quality
        if scenario == "fixture":
            return self.fixture
        raise ValueError("Unknown quality scenario")


def validate_run(run: Object, count: int) -> None:
    positive = (
        "recording_count",
        "source_rows",
        "clean_rows",
        "metadata_rows",
        "joined_rows",
        "parquet_readback_rows",
        "summary_groups",
        "minute_window_groups",
        "source_files",
        "simulated_replay_batches",
        "analytics_window_seconds",
    )
    fields(
        run,
        (
            *positive,
            "format",
            "provenance",
            "recording_ids",
            "runtime",
            "completed_at_utc",
            "elapsed_seconds",
            "source_missing_by_measure",
            "clean_missing_by_measure",
            "invalid_time_rows_dropped",
            "duplicate_key_rows_dropped",
        ),
        RUN,
    )
    require(all(integer(run[k], 1) for k in positive), RUN, "jumlah baris atau ukuran tidak valid")
    require(
        run["format"] == RUN_FORMAT and run["provenance"] == SOURCE_KIND,
        RUN,
        "format atau provenance tidak didukung",
    )
    require(
        run["recording_ids"] == recording_ids(count)
        and run["recording_count"] == run["metadata_rows"] == run["summary_groups"] == count
        and run["source_files"] == count * 2,
        RUN,
        "identitas run tidak cocok dengan mode",
    )
    require(
        run["clean_rows"] == run["joined_rows"] == run["parquet_readback_rows"],
        RUN,
        "jumlah observasi bersih, join, dan Parquet berbeda",
    )
    counts(run, ("invalid_time_rows_dropped", "duplicate_key_rows_dropped"), RUN)
    require(
        run["source_rows"]
        == run["clean_rows"] + run["invalid_time_rows_dropped"] + run["duplicate_key_rows_dropped"],
        RUN,
        "rekonsiliasi baris gagal",
    )
    for key in ("source_missing_by_measure", "clean_missing_by_measure"):
        counts(run[key], MEASURES, RUN)
    runtime = fields(
        run["runtime"], ("java", "machine", "os", "python", "spark", "spark_master"), RUN
    )
    require(
        all(
            isinstance(runtime[k], str) and runtime[k]
            for k in ("java", "machine", "os", "python", "spark", "spark_master")
        ),
        RUN,
        "informasi runtime tidak valid",
    )
    require(number(run["elapsed_seconds"]), RUN, "durasi run tidak valid")
    try:
        stamp(run["completed_at_utc"])
    except (ValueError, TypeError) as exc:
        raise EvidenceError(RUN, "timestamp run tidak valid") from exc


def validate_quality(report: Object, file: str, kind: str) -> None:
    fields(report, ("provenance", "before", "after", "actions"), file)
    require(report["provenance"] == kind, file, "provenance skenario tidak sesuai")
    before = fields(
        report["before"],
        (
            "rows",
            "invalid_time_rows",
            "incomplete_rows",
            "source_missing_by_measure",
            "exact_duplicate_source_rows_beyond_first",
            "repeated_valid_keys",
            "field_status_counts",
        ),
        file,
    )
    counts(
        before,
        (
            "rows",
            "invalid_time_rows",
            "incomplete_rows",
            "exact_duplicate_source_rows_beyond_first",
        ),
        file,
    )
    counts(before["repeated_valid_keys"], ("groups", "conflicting_groups", "excess_rows"), file)
    missing = counts(before["source_missing_by_measure"], MEASURES, file)
    after = counts(
        report["after"],
        ("rows", "invalid_time_rows", "incomplete_rows", "duplicate_key_rows"),
        file,
    )
    after_missing = counts(after.get("missing_by_measure"), MEASURES, file)
    actions = counts(
        report["actions"],
        ("invalid_time_rows_dropped", "duplicate_key_rows_dropped", "imputed_cells"),
        file,
    )
    converted = counts(
        actions.get("invalid_measure_cells_marked_missing_before_row_removals"), MEASURES, file
    )
    status = fields(before["field_status_counts"], NUMERIC_FIELDS, file)
    for channel in NUMERIC_FIELDS:
        item = counts(
            status[channel],
            ("valid", "blank", "nan", "malformed", "nonfinite", "out_of_range"),
            file,
        )
        require(
            sum(
                item[key]
                for key in ("valid", "blank", "nan", "malformed", "nonfinite", "out_of_range")
            )
            == before["rows"],
            file,
            "status sel tidak merekonsiliasi",
        )
        if channel in MEASURES:
            require(
                missing[channel] == item["blank"] + item["nan"]
                and converted[channel]
                == item["malformed"] + item["nonfinite"] + item["out_of_range"]
                and after_missing[channel] <= after["rows"],
                file,
                "jumlah sel hilang tidak merekonsiliasi",
            )
    require(
        before["rows"]
        - actions["invalid_time_rows_dropped"]
        - actions["duplicate_key_rows_dropped"]
        == after["rows"]
        and before["invalid_time_rows"] == actions["invalid_time_rows_dropped"]
        and before["repeated_valid_keys"]["excess_rows"] == actions["duplicate_key_rows_dropped"]
        and not any(
            (after["invalid_time_rows"], after["duplicate_key_rows"], actions["imputed_cells"])
        ),
        file,
        "rekonsiliasi validasi gagal",
    )
    if kind == SOURCE_KIND:
        by_record = list_field(report.get("invalid_time_rows_by_recording"), file)
        for row in by_record:
            fields(row, ("recording_id", "invalid_time_rows"), file)
            counts(row, ("invalid_time_rows",), file)
        require(
            sum(row["invalid_time_rows"] for row in by_record) == before["invalid_time_rows"],
            file,
            "jumlah timestamp per recording tidak cocok",
        )


def validate_provenance(provenance: Object, ids: list[str]) -> None:
    file = PROVENANCE
    fields(
        provenance,
        ("checksum_manifest", "dataset", "dataset_page", "doi", "files", "license", "version"),
        file,
    )
    for key in ("dataset", "dataset_page", "doi", "license", "version"):
        require(isinstance(provenance[key], str) and provenance[key], file, f"{key} tidak valid")
    require(
        provenance["dataset_page"] == DATASET_PAGE and provenance["version"] == DATASET_VERSION,
        file,
        "halaman atau versi dataset tidak sesuai",
    )
    checksum = fields(provenance["checksum_manifest"], ("sha256", "status", "url"), file)

    def sha(value: Any) -> bool:
        return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None

    require(
        sha(checksum["sha256"]) and checksum["url"] == SOURCE_BASE + "SHA256SUMS.txt",
        file,
        "manifest SHA-256 tidak sesuai",
    )
    expected = {
        f"bidmc_csv/{rid}_{suffix}" for rid in ids for suffix in ("Numerics.csv", "Fix.txt")
    }
    seen = set()
    for item in list_field(provenance["files"], file, nonempty=True):
        fields(item, ("bytes", "recording_id", "relative_path", "sha256", "status", "url"), file)
        path = item["relative_path"]
        require(
            isinstance(path, str)
            and path in expected - seen
            and item["recording_id"] in ids
            and path.startswith(f"bidmc_csv/{item['recording_id']}_")
            and item["url"] == SOURCE_BASE + path
            and sha(item["sha256"])
            and integer(item["bytes"], 1)
            and item["status"] in ("cached", "downloaded"),
            file,
            "sumber, checksum, atau status cache tidak valid",
        )
        seen.add(path)
    require(seen == expected, file, "daftar berkas sumber tidak lengkap")


def read_metadata(root: Path, ids: list[str], version: str) -> dict[str, Object]:
    file = METADATA
    try:
        rows = [
            json.loads(line)
            for line in (root / file).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(file, "JSON Lines tidak dapat dibaca") from exc
    result = {}
    for row in rows:
        fields(row, METADATA_FIELDS, file)
        rid = row["recording_id"]
        require(
            isinstance(rid, str) and rid in ids and rid not in result,
            file,
            "recording_id tidak cocok atau duplikat",
        )
        require(
            isinstance(row["location"], str)
            and row["location"].strip()
            and all(
                number(row[k]) and row[k] > 0
                for k in ("numerics_sampling_hz", "signals_sampling_hz")
            )
            and list_field(row["numeric_channels"], file, nonempty=True)
            and all(isinstance(channel, str) for channel in row["numeric_channels"])
            and row["dataset_version"] == version
            and row["source_fix_url"] == f"{SOURCE_BASE}bidmc_csv/{rid}_Fix.txt",
            file,
            "metadata Fix tidak sesuai",
        )
        result[rid] = {key: row[key] for key in METADATA_FIELDS}
    require(set(result) == set(ids), file, "metadata recording tidak lengkap")
    return result


def validate_integration(integration: Object, run: Object) -> None:
    file = INTEGRATION
    fields(
        integration,
        (
            *KEY_CHECKS,
            "expected_relationship",
            "metadata_rows",
            "observations_after_join",
            "observations_before_join",
            "csv_spark_types",
            "json_spark_types",
            "integrated_spark_types",
            "sample_joined_observations",
        ),
        file,
    )
    require(
        all(integration[key] == [] for key in KEY_CHECKS)
        and integration["expected_relationship"] == "many-to-one"
        and integration["metadata_rows"] == run["metadata_rows"]
        and integration["observations_after_join"]
        == integration["observations_before_join"]
        == run["joined_rows"],
        file,
        "kunci atau kardinalitas join tidak sesuai",
    )
    for key in ("csv_spark_types", "json_spark_types", "integrated_spark_types"):
        rows = list_field(integration[key], file, nonempty=True)
        require(
            all(
                isinstance(row, list)
                and len(row) == 2
                and all(isinstance(value, str) for value in row)
                for row in rows
            )
            and "recording_id" in dict(rows),
            file,
            "skema Spark tidak valid",
        )
    require(
        all(
            dict(integration["csv_spark_types"]).get(key) == "string"
            and dict(integration["integrated_spark_types"]).get(key) == "double"
            for key in NUMERIC_FIELDS
        ),
        file,
        "tipe kolom numerik tidak sesuai",
    )
    for row in list_field(integration["sample_joined_observations"], file, nonempty=True):
        fields(row, (*METADATA_FIELDS, *NUMERIC_FIELDS), file)
        require(
            row["recording_id"] in run["recording_ids"]
            and number(row["time_s"])
            and all(row[k] is None or number(row[k]) for k in MEASURES),
            file,
            "sampel join tidak valid",
        )


def validate_profiles(value: Object, run: Object) -> list[Object]:
    file = SCHEMA
    profiles = list_field(value.get("recordings"), file, nonempty=True)
    for item in profiles:
        fields(item, ("recording_id", "rows", "header", "fields", "lexical_types"), file)
        require(
            integer(item["rows"], 1)
            and isinstance(item["header"], list)
            and len(item["header"]) == len(NUMERIC_FIELDS)
            and all(isinstance(h, str) for h in item["header"])
            and isinstance(item["fields"], list)
            and all(isinstance(field, str) for field in item["fields"])
            and sorted(item["fields"]) == sorted(NUMERIC_FIELDS),
            file,
            "header atau kolom numerik tidak sesuai",
        )
        for group in fields(item["lexical_types"], NUMERIC_FIELDS, file).values():
            require(
                isinstance(group, dict)
                and all(integer(n) for n in group.values())
                and sum(group.values()) == item["rows"],
                file,
                "profil token tidak sesuai",
            )
    require(
        [item["recording_id"] for item in profiles] == run["recording_ids"]
        and sum(item["rows"] for item in profiles) == run["source_rows"],
        file,
        "daftar recording atau jumlah baris tidak cocok",
    )
    return profiles


def validate_volume(volume: Object, run: Object) -> None:
    file = VOLUME
    fields(
        volume,
        (
            "trials",
            "median_ms",
            "output_groups",
            "clean_observation_rows",
            "metadata_rows_for_join",
            "master",
            "shuffle_partitions",
            "adaptive_query_execution",
            "window_seconds",
            "spark_version",
        ),
        file,
    )
    groups = counts(volume["output_groups"], OPERATIONS, file)
    medians = fields(volume["median_ms"], OPERATIONS, file)
    require(
        volume["clean_observation_rows"] == run["clean_rows"]
        and volume["metadata_rows_for_join"] == run["metadata_rows"]
        and groups["aggregation"] == run["summary_groups"]
        and groups["join_and_window"] == run["minute_window_groups"]
        and volume["window_seconds"] == run["analytics_window_seconds"]
        and integer(volume["shuffle_partitions"], 1),
        file,
        "benchmark bukan dari run ini",
    )
    trials: dict[str, dict] = {operation: {} for operation in OPERATIONS}
    for trial in list_field(volume["trials"], file, nonempty=True):
        fields(trial, ("operation", "trial", "elapsed_ms"), file)
        op, ordinal, elapsed = trial["operation"], trial["trial"], trial["elapsed_ms"]
        require(
            isinstance(op, str)
            and op in trials
            and integer(ordinal, 1)
            and ordinal not in trials[op]
            and number(elapsed),
            file,
            "trial tidak valid",
        )
        trials[op][ordinal] = elapsed
    for op in OPERATIONS:
        require(
            bool(trials[op])
            and number(medians[op])
            and math.isclose(median(trials[op].values()), medians[op], abs_tol=0.001),
            file,
            "median tidak cocok dengan trial yang diukur",
        )


def validate_velocity(value: Object, run: Object) -> None:
    file = VELOCITY
    fields(
        value,
        (
            "batches",
            "provenance",
            "target_arrival_interval_s",
            "source_window_seconds",
            "total_processed_rows",
            "total_valid_time_rows",
        ),
        file,
    )
    batches = list_field(value["batches"], file, nonempty=True)
    require(
        value["provenance"] == "historical_bidmc_local_timed_replay"
        and number(value["target_arrival_interval_s"])
        and value["target_arrival_interval_s"] > 0
        and integer(value["source_window_seconds"], 1)
        and len(batches) == run["simulated_replay_batches"],
        file,
        "identitas replay tidak cocok",
    )
    stamps = ("arrived_at_utc", "processing_started_at_utc", "completed_at_utc")
    for index, batch in enumerate(batches, 1):
        fields(
            batch,
            (
                "batch",
                "processed_rows",
                "valid_time_rows",
                "source_window_start_s",
                "source_window_end_s_exclusive",
                "arrival_interval_ms",
                *stamps,
                "queue_wait_ms",
                "spark_ingest_and_process_ms",
                "arrival_to_completion_ms",
            ),
            file,
        )
        gap = batch["arrival_interval_ms"]
        start, end = batch["source_window_start_s"], batch["source_window_end_s_exclusive"]
        require(
            (start is None and end is None)
            or (integer(start) and end == start + value["source_window_seconds"]),
            file,
            "batas jendela batch tidak valid",
        )
        require(
            batch["batch"] == index
            and integer(batch["processed_rows"], 1)
            and integer(batch["valid_time_rows"])
            and batch["valid_time_rows"] <= batch["processed_rows"]
            and (gap is None if index == 1 else number(gap))
            and all(
                number(batch[key])
                for key in ("spark_ingest_and_process_ms", "arrival_to_completion_ms")
            )
            and (batch["queue_wait_ms"] is None or number(batch["queue_wait_ms"])),
            file,
            "jumlah, interval, atau latency batch tidak valid",
        )
        if batch["queue_wait_ms"] is not None:
            require(
                math.isclose(
                    batch["arrival_to_completion_ms"],
                    batch["queue_wait_ms"] + batch["spark_ingest_and_process_ms"],
                    abs_tol=0.002,
                ),
                file,
                "latency batch tidak merekonsiliasi",
            )
        try:
            for key in stamps:
                stamp(batch[key])
        except (TypeError, ValueError) as exc:
            raise EvidenceError(file, "timestamp replay tidak valid") from exc
    require(
        sum(b["processed_rows"] for b in batches)
        == value["total_processed_rows"]
        == run["source_rows"]
        and sum(b["valid_time_rows"] for b in batches)
        == value["total_valid_time_rows"]
        == run["source_rows"] - run["invalid_time_rows_dropped"],
        file,
        "jumlah replay tidak merekonsiliasi dengan run",
    )


def analytics_csv(root: Path, name: str, run: Object) -> pd.DataFrame:
    base = (
        ("recording_id", "location") if name == RECORDINGS else ("recording_id", "window_start_s")
    )
    numeric = (
        "rows",
        "first_time_s",
        "last_time_s",
        *(
            f"{c}_{kind}"
            for c in MEASURES
            for kind in ("valid", "completeness", "min", "mean", "max")
        ),
    )
    frame = read_csv(root, name, (*base, *numeric))
    require(
        set(frame["recording_id"]) == set(run["recording_ids"]), name, "recording_id tidak cocok"
    )
    key = ["recording_id"] if name == RECORDINGS else list(base)
    require(not frame.duplicated(key).any(), name, "kunci ringkasan SQL duplikat")
    for col in numeric if name == RECORDINGS else (*numeric, "window_start_s"):
        data = pd.to_numeric(frame[col], errors="coerce")
        require(
            not (frame[col].notna() & (data.isna() | data.isin([math.inf, -math.inf]))).any(),
            name,
            f"nilai non-numerik atau tak hingga di {col}",
        )
        frame[col] = data
    require(
        frame["rows"].notna().all()
        and (frame["rows"] >= 1).all()
        and (frame["rows"] % 1 == 0).all()
        and frame["rows"].sum() == run["clean_rows"]
        and len(frame) == run["summary_groups" if name == RECORDINGS else "minute_window_groups"],
        name,
        "jumlah baris ringkasan tidak cocok",
    )
    require(
        (frame["first_time_s"] >= 0).all()
        and (frame["last_time_s"] >= frame["first_time_s"]).all(),
        name,
        "rentang waktu tidak valid",
    )
    if name == WINDOWS:
        width = run["analytics_window_seconds"]
        require(
            (frame["window_start_s"] >= 0).all()
            and (frame["window_start_s"] % width == 0).all()
            and (frame["first_time_s"] >= frame["window_start_s"]).all()
            and (frame["last_time_s"] < frame["window_start_s"] + width).all(),
            name,
            "waktu observasi berada di luar jendela SQL",
        )
    for c in MEASURES:
        valid = frame[f"{c}_valid"]
        require(
            valid.notna().all()
            and (valid % 1 == 0).all()
            and ((valid >= 0) & (valid <= frame["rows"])).all()
            and (frame[f"{c}_completeness"].sub(valid / frame["rows"]).abs() <= 0.000001).all()
            and int((frame["rows"] - valid).sum()) == run["clean_missing_by_measure"][c],
            name,
            f"kelengkapan {c} tidak cocok dengan audit",
        )
        present = valid > 0
        for kind in ("min", "mean", "max"):
            series = frame[f"{c}_{kind}"]
            require(
                (series.notna() == present).all() and (series[present] >= 0).all(),
                name,
                f"statistik {c} tidak cocok dengan jumlah pengukuran valid",
            )
        require(
            (frame.loc[present, f"{c}_min"] <= frame.loc[present, f"{c}_mean"]).all()
            and (frame.loc[present, f"{c}_mean"] <= frame.loc[present, f"{c}_max"]).all(),
            name,
            f"minimum, rata-rata atau maksimum {c} tidak valid",
        )
    return frame.sort_values(key, ignore_index=True)


class EvidenceRepository:
    def __init__(self, project: Project):
        self.project = project

    def path(self, mode: str) -> Path:
        if mode not in MODES:
            raise EvidenceError(RUN, "mode dataset tidak didukung")
        return self.project.result(MODES[mode])

    def revision(self, mode: str, *, detail: bool = False) -> Revision:
        root = self.path(mode)
        files = [root / name for name in REQUIRED]
        if detail:
            parts = sorted((root / PARQUET).glob("*.parquet"))
            require(bool(parts), PARQUET, "data Parquet tidak tersedia")
            files += parts
        stats = []
        for path in files:
            name = path.relative_to(root).as_posix()
            try:
                require(path.is_file(), name, "berkas tidak ditemukan")
                stat = path.stat()
            except OSError as exc:
                raise EvidenceError(name, "berkas tidak dapat diakses") from exc
            stats.append((name, stat.st_ino, stat.st_size, stat.st_mtime_ns))
        return tuple(stats)

    def load(self, mode: str, revision: Revision | None = None) -> Snapshot:
        root = self.path(mode)
        revision = revision if revision is not None else self.revision(mode)
        run = read_object(root, RUN)
        validate_run(run, MODES[mode])
        ids = run["recording_ids"]
        provenance = read_object(root, PROVENANCE)
        validate_provenance(provenance, ids)
        metadata = read_metadata(root, ids, provenance["version"])
        profiles = validate_profiles(read_object(root, SCHEMA), run)
        integration = read_object(root, INTEGRATION)
        validate_integration(integration, run)
        quality, fixture = read_object(root, QUALITY), read_object(root, FIXTURE)
        validate_quality(quality, QUALITY, SOURCE_KIND)
        validate_quality(fixture, FIXTURE, FIXTURE_KIND)
        require(
            quality["before"]["rows"] == run["source_rows"]
            and quality["after"]["rows"] == run["clean_rows"]
            and quality["before"]["source_missing_by_measure"] == run["source_missing_by_measure"]
            and quality["after"]["missing_by_measure"] == run["clean_missing_by_measure"]
            and quality["actions"]["invalid_time_rows_dropped"] == run["invalid_time_rows_dropped"]
            and quality["actions"]["duplicate_key_rows_dropped"]
            == run["duplicate_key_rows_dropped"]
            and all(
                row["recording_id"] in ids for row in quality["invalid_time_rows_by_recording"]
            ),
            QUALITY,
            "laporan audit bukan dari run ini",
        )
        recordings = analytics_csv(root, RECORDINGS, run)
        windows = analytics_csv(root, WINDOWS, run)
        sums = ["rows", *(f"{c}_valid" for c in MEASURES)]
        require(
            windows.groupby("recording_id")[sums]
            .sum()
            .equals(recordings.set_index("recording_id")[sums]),
            WINDOWS,
            "jumlah per recording tidak cocok dengan ringkasan SQL",
        )
        require(
            all(
                row.location == metadata[row.recording_id]["location"]
                for row in recordings.itertuples()
            ),
            RECORDINGS,
            "lokasi tidak cocok dengan metadata",
        )
        coverage = read_csv(
            root,
            COVERAGE,
            (
                "recording_id",
                "expected_step_s",
                "first_time_s",
                "last_time_s",
                "max_observed_step_s",
                "long_intervals",
                "short_intervals",
            ),
        )
        require(
            sorted(coverage["recording_id"].fillna("")) == sorted(ids),
            COVERAGE,
            "cakupan waktu tidak cocok dengan daftar recording",
        )
        for key in (
            "expected_step_s",
            "first_time_s",
            "last_time_s",
            "max_observed_step_s",
            "long_intervals",
            "short_intervals",
        ):
            column = pd.to_numeric(coverage[key], errors="coerce")
            require(
                not (coverage[key].notna() & column.isna()).any()
                and not column.isin([math.inf, -math.inf]).any()
                and (column.dropna() >= 0).all()
                and (key == "max_observed_step_s" or column.notna().all()),
                COVERAGE,
                f"nilai cakupan waktu tidak valid: {key}",
            )
            if key in ("long_intervals", "short_intervals"):
                require((column % 1 == 0).all(), COVERAGE, f"jumlah interval tidak valid: {key}")
            coverage[key] = column
        require(
            all(
                math.isclose(
                    row.expected_step_s, 1 / metadata[row.recording_id]["numerics_sampling_hz"]
                )
                for row in coverage.itertuples()
            ),
            COVERAGE,
            "frekuensi tidak cocok dengan metadata",
        )
        require(
            all(
                sum(
                    item["lexical_types"][key].get(state, 0)
                    for item in profiles
                    for state in ("blank", "nan")
                )
                == run["source_missing_by_measure"][key]
                for key in MEASURES
            ),
            SCHEMA,
            "jumlah nilai hilang pada profil tidak cocok dengan audit sumber",
        )
        volume, velocity = read_object(root, VOLUME), read_object(root, VELOCITY)
        validate_volume(volume, run)
        validate_velocity(velocity, run)
        metrics = Metrics(
            len(ids),
            run["source_rows"],
            run["clean_rows"],
            sum(run["clean_missing_by_measure"].values()),
            run["clean_rows"] * len(MEASURES),
            median(b["arrival_to_completion_ms"] for b in velocity["batches"]),
            median(b["spark_ingest_and_process_ms"] for b in velocity["batches"]),
        )
        require(revision == self.revision(mode), RUN, "run baru sedang dipublikasikan; muat ulang")
        return Snapshot(
            mode,
            revision,
            run,
            provenance,
            profiles,
            integration,
            metadata,
            quality,
            fixture,
            coverage,
            recordings,
            windows,
            volume,
            velocity,
            metrics,
        )

    def recording(
        self, mode: str, recording: str, expected_rows: int, revision: Revision
    ) -> pd.DataFrame:
        root = self.path(mode)
        require(
            recording in recording_ids(MODES[mode]),
            PARQUET,
            "recording_id tidak ada pada mode yang dipilih",
        )
        try:
            dataset = ds.dataset(root / PARQUET, format="parquet")
            result = dataset.to_table(
                columns=["recording_id", *NUMERIC_FIELDS],
                filter=ds.field("recording_id") == recording,
            ).to_pandas()
        except (OSError, ValueError, TypeError) as exc:
            raise EvidenceError(
                PARQUET, "data Parquet tidak dapat dibaca atau kolom tidak sesuai"
            ) from exc
        require(
            len(result) == expected_rows
            and not result["time_s"].duplicated().any()
            and result["time_s"].notna().all(),
            PARQUET,
            "observasi tidak cocok dengan ringkasan run",
        )
        for key in NUMERIC_FIELDS:
            require(
                pd.api.types.is_numeric_dtype(result[key])
                and not result[key].isin([math.inf, -math.inf]).any()
                and (result[key].dropna() >= 0).all(),
                PARQUET,
                f"nilai kolom {key} tidak valid",
            )
        require(
            revision == self.revision(mode, detail=True),
            PARQUET,
            "run baru sedang dipublikasikan; muat ulang",
        )
        return result.sort_values("time_s", ignore_index=True)
