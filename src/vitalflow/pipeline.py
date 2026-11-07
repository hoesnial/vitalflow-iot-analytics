"""Run the audited pipeline and publish one validated result snapshot."""

import logging
import platform
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from .acquisition import acquire
from .analytics import compare_operations, summaries
from .artifacts import RUN_FORMAT, staged_result, write_csv, write_json
from .config import REPLAY_INTERVAL_SECONDS, WINDOW_SECONDS, Project, VitalFlowError
from .integration import derive_metadata, join_observations, verify_metadata
from .quality import audit, classify_rows, clean_rows, time_coverage
from .replay import replay, utc_now
from .spark import REPLAY_COLUMNS, csv_strings, read_sources

LOG = logging.getLogger(__name__)
OFFICIAL = "physionet_bidmc_original"
CONTROLLED = "synthetic_controlled_fixture_not_physionet"


@dataclass(frozen=True)
class RunOptions:
    count: int
    replay_interval_s: float = REPLAY_INTERVAL_SECONDS

    def __post_init__(self) -> None:
        if not 0 < self.replay_interval_s <= 60:
            raise VitalFlowError("Replay interval must be greater than 0 and at most 60 seconds.")


def rows_as_dicts(frame: DataFrame) -> list[dict]:
    return [row.asDict(recursive=True) for row in frame.collect()]


def roundtrip(spark: SparkSession, joined: DataFrame, path: Path, expected: int) -> DataFrame:
    path.parent.mkdir(parents=True, exist_ok=True)
    joined.write.mode("errorifexists").parquet(path.as_uri())
    stored = spark.read.parquet(path.as_uri())
    actual = stored.count()
    if actual != expected or stored.dtypes != joined.dtypes:
        raise VitalFlowError(
            f"Parquet verification failed: expected {expected} rows with the integrated "
            f"schema, read {actual} rows."
        )
    return stored


def write_source_quality(
    destination: Path, raw: DataFrame, typed: DataFrame, clean: DataFrame
) -> dict:
    report = audit(raw, typed, clean, provenance=OFFICIAL)
    invalid_by_recording = (
        typed.where(F.col("time_s").isNull())
        .groupBy("recording_id")
        .agg(F.count("*").alias("invalid_time_rows"))
        .orderBy("recording_id")
    )
    report["invalid_time_rows_by_recording"] = rows_as_dicts(invalid_by_recording)
    write_json(destination / "source.json", report)
    return report


def write_controlled_quality(spark: SparkSession, project: Project, destination: Path) -> None:
    fixture = project.root / "data" / "scenarios" / "controlled_quality.csv"
    raw = csv_strings(spark, [fixture], REPLAY_COLUMNS)
    typed = classify_rows(raw)
    write_json(
        destination / "controlled_fixture.json",
        audit(raw, typed, clean_rows(typed), provenance=CONTROLLED),
    )


def run(spark: SparkSession, project: Project, options: RunOptions) -> dict:
    start = perf_counter()
    records, manifest = acquire(project, options.count, offline=True)
    with staged_result(project, options.count) as stage:
        LOG.info("Inspecting and reading %d verified recording pairs.", options.count)
        raw, profiles = read_sources(spark, records)
        raw.cache()
        typed = classify_rows(raw).cache()
        clean = clean_rows(typed).cache()
        metadata = derive_metadata(spark, records, stage / "data" / "metadata" / "recordings.jsonl")
        metadata.cache()
        parquet = None
        joined = None
        try:
            join_report = verify_metadata(
                raw, metadata, [record.recording_id for record in records]
            )
            quality = write_source_quality(stage / "quality", raw, typed, clean)
            source_rows = quality["before"]["rows"]
            clean_rows_count = quality["after"]["rows"]
            if source_rows != sum(profile["rows"] for profile in profiles):
                raise VitalFlowError("Spark source row count disagrees with CSV preflight.")
            if not clean_rows_count:
                raise VitalFlowError("No observations have a valid time key.")
            LOG.info(
                "Validated %d input rows; %d observations retained.", source_rows, clean_rows_count
            )
            joined = join_observations(clean, metadata).cache()
            joined_count = joined.count()
            if joined_count != clean_rows_count:
                raise VitalFlowError("CSV/JSON join changed the number of observations.")
            sample = rows_as_dicts(joined.orderBy("recording_id", "time_s").limit(3))
            write_json(
                stage / "integration.json",
                {
                    **join_report,
                    "observations_before_join": clean_rows_count,
                    "observations_after_join": joined_count,
                    "csv_spark_types": raw.dtypes,
                    "json_spark_types": metadata.dtypes,
                    "integrated_spark_types": joined.dtypes,
                    "sample_joined_observations": sample,
                },
            )
            write_json(stage / "provenance.json", manifest)
            write_json(stage / "source_schema.json", {"recordings": profiles})

            LOG.info("Writing and verifying Parquet, then executing Spark SQL summaries.")
            parquet = roundtrip(
                spark, joined, stage / "data" / "processed" / "observations.parquet", joined_count
            ).cache()
            per_record, windows = summaries(spark, parquet)
            recording_rows, window_rows = rows_as_dicts(per_record), rows_as_dicts(windows)
            if (
                len(recording_rows) != options.count
                or sum(row["rows"] for row in recording_rows) != joined_count
                or sum(row["rows"] for row in window_rows) != joined_count
            ):
                raise VitalFlowError("SQL summaries did not account for every recording and row.")
            write_csv(stage / "analytics" / "by_recording.csv", recording_rows)
            write_csv(stage / "analytics" / "by_minute.csv", window_rows)
            write_csv(
                stage / "quality" / "time_coverage.csv", rows_as_dicts(time_coverage(parquet))
            )
            write_controlled_quality(spark, project, stage / "quality")

            LOG.info("Measuring Spark operations and running timed historical replay.")
            benchmark, plans = compare_operations(
                spark, clean, metadata, clean_rows_count, join_report["metadata_rows"]
            )
            write_json(stage / "benchmarks" / "volume.json", benchmark)
            for name, plan in plans.items():
                (stage / "benchmarks" / f"{name}_plan.txt").write_text(plan, encoding="utf-8")
            replay_report = replay(spark, records, options.replay_interval_s)
            if (
                replay_report["total_processed_rows"] != source_rows
                or replay_report["total_valid_time_rows"]
                != source_rows - quality["before"]["invalid_time_rows"]
            ):
                raise VitalFlowError("Timed replay does not reconcile with the source audit.")
            write_json(stage / "benchmarks" / "velocity.json", replay_report)
            write_csv(stage / "benchmarks" / "velocity_batches.csv", replay_report["batches"])

            result = {
                "format": RUN_FORMAT,
                "provenance": OFFICIAL,
                "recording_count": options.count,
                "recording_ids": [record.recording_id for record in records],
                "source_files": len(manifest["files"]),
                "source_rows": source_rows,
                "clean_rows": clean_rows_count,
                "metadata_rows": join_report["metadata_rows"],
                "joined_rows": joined_count,
                "parquet_readback_rows": joined_count,
                "summary_groups": len(recording_rows),
                "minute_window_groups": len(window_rows),
                "analytics_window_seconds": WINDOW_SECONDS,
                "source_missing_by_measure": quality["before"]["source_missing_by_measure"],
                "clean_missing_by_measure": quality["after"]["missing_by_measure"],
                "invalid_time_rows_dropped": quality["actions"]["invalid_time_rows_dropped"],
                "duplicate_key_rows_dropped": quality["actions"]["duplicate_key_rows_dropped"],
                "simulated_replay_batches": len(replay_report["batches"]),
                "runtime": {
                    "spark": spark.version,
                    "spark_master": spark.sparkContext.master,
                    "python": platform.python_version(),
                    "os": platform.system(),
                    "machine": platform.machine(),
                    "java": spark.sparkContext._jvm.java.lang.System.getProperty("java.version"),
                },
                "elapsed_seconds": round(perf_counter() - start, 3),
                "completed_at_utc": utc_now(),
            }
            write_json(stage / "run.json", result)
        finally:
            for frame in (parquet, joined, metadata, clean, typed, raw):
                if frame is not None:
                    frame.unpersist()
    LOG.info("Published %s", project.result(options.count))
    return result
