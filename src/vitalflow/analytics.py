"""Spark SQL summaries and a measured DataFrame operation comparison."""

import io
from contextlib import redirect_stdout
from statistics import median
from time import perf_counter

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from .config import BENCHMARK_TRIALS, WINDOW_SECONDS, VitalFlowError
from .integration import join_observations
from .source import MEASURES


def summaries(spark: SparkSession, parquet: DataFrame) -> tuple[DataFrame, DataFrame]:
    parquet.createOrReplaceTempView("vitalflow_observations")
    measures = ",\n".join(
        f"COUNT({field}) AS {field}_valid, "
        f"ROUND(COUNT({field}) / COUNT(*), 6) AS {field}_completeness, "
        f"MIN({field}) AS {field}_min, ROUND(AVG({field}), 4) AS {field}_mean, "
        f"MAX({field}) AS {field}_max"
        for field in MEASURES
    )
    selection = (
        f"COUNT(*) AS rows, MIN(time_s) AS first_time_s, MAX(time_s) AS last_time_s, {measures}"
    )
    per_recording = spark.sql(f"""
        SELECT recording_id, location, {selection}
        FROM vitalflow_observations
        GROUP BY recording_id, location ORDER BY recording_id
    """)
    by_window = spark.sql(f"""
        SELECT recording_id, FLOOR(time_s / {WINDOW_SECONDS}) * {WINDOW_SECONDS} AS window_start_s,
               {selection}
        FROM vitalflow_observations
        GROUP BY recording_id, window_start_s ORDER BY recording_id, window_start_s
    """)
    return per_recording, by_window


def compare_operations(
    spark: SparkSession,
    clean: DataFrame,
    metadata: DataFrame,
    clean_count: int,
    metadata_count: int,
) -> tuple[dict, dict[str, str]]:
    queries = {
        "aggregation": clean.groupBy("recording_id").agg(F.count("*").alias("observations")),
        "join_and_window": (
            join_observations(clean, metadata)
            .withColumn(
                "window_start_s", F.floor(F.col("time_s") / WINDOW_SECONDS) * WINDOW_SECONDS
            )
            .groupBy("recording_id", "location", "window_start_s")
            .agg(F.count("*").alias("observations"))
        ),
    }
    # Both operations use the same cached observations. Warm once, then alternate execution order.
    output_counts = {}
    for name, query in queries.items():
        rows = query.collect()
        if sum(row.observations for row in rows) != clean_count:
            raise VitalFlowError(f"Benchmark {name} did not account for every cleaned observation.")
        output_counts[name] = len(rows)
    trials: list[dict] = []
    names = list(queries)
    for trial in range(BENCHMARK_TRIALS):
        order = names if trial % 2 == 0 else list(reversed(names))
        for name in order:
            start = perf_counter()
            queries[name].collect()
            trials.append(
                {
                    "trial": trial + 1,
                    "operation": name,
                    "elapsed_ms": round((perf_counter() - start) * 1000, 3),
                }
            )
    plans = {}
    for name, query in queries.items():
        with redirect_stdout(io.StringIO()) as result:
            query.explain(mode="formatted")
        plans[name] = result.getvalue()
    return {
        "protocol": "Warm local Spark actions; same cached observations; includes driver collect.",
        "master": spark.sparkContext.master,
        "spark_version": spark.version,
        "shuffle_partitions": int(spark.conf.get("spark.sql.shuffle.partitions")),
        "adaptive_query_execution": spark.conf.get("spark.sql.adaptive.enabled") == "true",
        "clean_observation_rows": clean_count,
        "metadata_rows_for_join": metadata_count,
        "output_groups": output_counts,
        "window_seconds": WINDOW_SECONDS,
        "trials": trials,
        "median_ms": {
            name: median(item["elapsed_ms"] for item in trials if item["operation"] == name)
            for name in names
        },
    }, plans
