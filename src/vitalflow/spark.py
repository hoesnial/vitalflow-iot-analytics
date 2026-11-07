"""Local Spark runtime, schemas and multi-recording CSV ingestion."""

import os
import sys
from collections import defaultdict
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T

from .config import MASTER, SHUFFLE_PARTITIONS
from .source import NUMERIC_FIELDS, SourceRecord, inspect_csv, normalize_header

REPLAY_COLUMNS = ("recording_id", *NUMERIC_FIELDS)


def session() -> SparkSession:
    # Python-created RDDs use SparkContext's environment setting, not just the JVM config.
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
    spark = (
        SparkSession.builder.appName("VitalFlow")
        .master(MASTER)
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.pyspark.python", sys.executable)
        .config("spark.executorEnv.PYSPARK_PYTHON", sys.executable)
        .config("spark.ui.enabled", "false")
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.sql.shuffle.partitions", str(SHUFFLE_PARTITIONS))
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.csv.parser.columnPruning.enabled", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def csv_strings(spark: SparkSession, paths: list[Path], columns: tuple[str, ...]) -> DataFrame:
    schema = T.StructType([T.StructField(name, T.StringType()) for name in columns])
    return (
        spark.read.schema(schema)
        .options(header=True, enforceSchema=False, mode="FAILFAST", escape='"')
        .csv([p.resolve().as_uri() for p in paths])
    )


def read_sources(spark: SparkSession, records: list[SourceRecord]) -> tuple[DataFrame, list[dict]]:
    # Each file is inspected, and layouts are grouped by exact header, never by a guessed order.
    layouts: dict[tuple[str, ...], list[Path]] = defaultdict(list)
    profiles = []
    for record in records:
        profile = inspect_csv(record.numerics.read_bytes(), record.numerics.name)
        layouts[tuple(profile["header"])].append(record.numerics)
        profiles.append({"recording_id": record.recording_id, **profile})
    frames = []
    for header, paths in layouts.items():
        names = normalize_header(list(header))
        frames.append(
            csv_strings(spark, paths, header).select(
                F.regexp_extract(
                    F.col("_metadata.file_name"), r"^(bidmc_[0-9]{2})_Numerics\.csv$", 1
                ).alias("recording_id"),
                *(
                    F.col(f"`{original}`").alias(normalized)
                    for original, normalized in zip(header, names, strict=True)
                ),
            )
        )
    combined = frames[0]
    for frame in frames[1:]:
        combined = combined.unionByName(frame)
    return combined.select(*REPLAY_COLUMNS), profiles
