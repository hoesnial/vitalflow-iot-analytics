"""Derived JSON metadata and guarded many-to-one integration."""

import json
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T

from .config import VitalFlowError
from .source import SourceRecord, parse_fix

METADATA_SCHEMA = T.StructType(
    [
        T.StructField("recording_id", T.StringType()),
        T.StructField("location", T.StringType()),
        T.StructField("signals_sampling_hz", T.DoubleType()),
        T.StructField("numerics_sampling_hz", T.DoubleType()),
        T.StructField("numeric_channels", T.ArrayType(T.StringType())),
        T.StructField("dataset_version", T.StringType()),
        T.StructField("source_fix_url", T.StringType()),
    ]
)


def derive_metadata(spark: SparkSession, records: list[SourceRecord], path: Path) -> DataFrame:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for record in records:
            metadata = parse_fix(record.fix.read_bytes(), record.recording_id)
            stream.write(json.dumps(metadata, sort_keys=True, allow_nan=False) + "\n")
    return spark.read.schema(METADATA_SCHEMA).option("mode", "FAILFAST").json(path.as_uri())


def verify_metadata(raw: DataFrame, metadata: DataFrame, expected_ids: list[str]) -> dict:
    expected = set(expected_ids)
    observed = {row.recording_id for row in raw.select("recording_id").distinct().collect()}
    metadata_counts = {
        row.recording_id: row["count"] for row in metadata.groupBy("recording_id").count().collect()
    }
    actual = set(metadata_counts)
    issues = {
        "missing_source_ids": sorted(expected - observed),
        "unexpected_source_ids": sorted(observed - expected, key=str),
        "source_ids_without_metadata": sorted(observed - actual, key=str),
        "metadata_ids_without_source": sorted(actual - observed, key=str),
        "duplicate_metadata_ids": sorted(
            (rid for rid, count in metadata_counts.items() if count > 1), key=str
        ),
    }
    if any(issues.values()):
        raise VitalFlowError(f"Recording/metadata identity check failed: {issues}")
    required_missing = F.greatest(*(F.col(f).isNull() for f in METADATA_SCHEMA.fieldNames()))
    if metadata.where(required_missing).limit(1).count():
        raise VitalFlowError("Derived JSON contains missing required metadata.")
    return {
        "metadata_rows": sum(metadata_counts.values()),
        "expected_relationship": "many-to-one",
        **issues,
    }


def join_observations(clean: DataFrame, metadata: DataFrame) -> DataFrame:
    # The verified lookup has at most 53 rows, small enough to broadcast.
    return clean.join(F.broadcast(metadata), "recording_id", "inner")
