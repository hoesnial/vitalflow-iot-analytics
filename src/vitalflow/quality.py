"""Audit, type and clean observations while preserving unavailable values."""

from pyspark.sql import Column, DataFrame, Window
from pyspark.sql import functions as F

from .source import MEASURES, NUMBER, NUMERIC_FIELDS

KEY = ("recording_id", "time_s")
REASONS = ("blank", "nan", "malformed", "nonfinite", "out_of_range")
# These are format/domain checks, not clinical reference ranges.
MINIMUM = 0.0
SPO2_MAXIMUM = 100.0
CADENCE_TOLERANCE_SECONDS = 1e-6


def classify(field: str) -> tuple[Column, Column]:
    raw = F.regexp_replace(F.coalesce(F.col(field), F.lit("")), r"^\s+|\s+$", "")
    parsed = raw.try_cast("double")
    nonfinite = F.lower(raw).rlike(r"^[+-]?inf(?:inity)?$") | (F.abs(parsed) == float("inf"))
    outside = parsed < MINIMUM
    if field == "spo2":
        outside = outside | (parsed > SPO2_MAXIMUM)
    status = (
        F.when(raw == "", "blank")
        .when(F.lower(raw) == "nan", "nan")
        .when(nonfinite, "nonfinite")
        .when(~raw.rlike(f"^{NUMBER}$") | parsed.isNull(), "malformed")
        .when(outside, "out_of_range")
        .otherwise("valid")
    )
    # Canonicalize negative zero so duplicate keys and output are stable.
    value = F.when(status == "valid", F.when(parsed == 0, 0.0).otherwise(parsed))
    return status, value


def classify_rows(raw: DataFrame) -> DataFrame:
    columns = [F.col("recording_id")]
    for field in NUMERIC_FIELDS:
        status, value = classify(field)
        columns.extend((value.alias(field), status.alias(f"{field}_status")))
    return raw.select(*columns)


def clean_rows(typed: DataFrame) -> DataFrame:
    valid_keys = typed.where(F.col("time_s").isNotNull())
    filled = sum((F.col(field).isNotNull().cast("int") for field in MEASURES), F.lit(0))
    ranking = Window.partitionBy(*KEY).orderBy(
        filled.desc(),
        *(F.col(field).asc_nulls_last() for field in MEASURES),
    )
    return (
        valid_keys.withColumn("_rank", F.row_number().over(ranking))
        .where(F.col("_rank") == 1)
        .select(*KEY, *MEASURES)
    )


def audit(raw: DataFrame, typed: DataFrame, clean: DataFrame, *, provenance: str) -> dict:
    before = (
        typed.agg(
            F.count("*").alias("rows"),
            F.count_if(F.col("time_s").isNull()).alias("invalid_time_rows"),
            F.count_if(F.greatest(*(F.col(m).isNull() for m in MEASURES))).alias("incomplete_rows"),
            *(
                F.count_if(F.col(f"{field}_status") == reason).alias(f"{field}_{reason}")
                for field in NUMERIC_FIELDS
                for reason in ("valid", *REASONS)
            ),
        )
        .first()
        .asDict()
    )
    raw_repeats = (
        raw.groupBy(*raw.columns)
        .count()
        .where(F.col("count") > 1)
        .agg(F.coalesce(F.sum(F.col("count") - 1), F.lit(0)).alias("rows"))
        .first()
        .rows
    )
    repeated = (
        typed.where(F.col("time_s").isNotNull())
        .groupBy(*KEY)
        .agg(F.count("*").alias("n"), F.count_distinct(F.struct(*MEASURES)).alias("variants"))
        .agg(
            F.count_if(F.col("n") > 1).alias("groups"),
            F.count_if(F.col("variants") > 1).alias("conflicting_groups"),
            F.coalesce(F.sum(F.col("n") - 1), F.lit(0)).alias("excess_rows"),
        )
        .first()
        .asDict()
    )
    after = (
        clean.agg(
            F.count("*").alias("rows"),
            F.count_if(F.col("time_s").isNull()).alias("invalid_time_rows"),
            F.count_if(F.greatest(*(F.col(m).isNull() for m in MEASURES))).alias("incomplete_rows"),
            *(F.count_if(F.col(field).isNull()).alias(field) for field in MEASURES),
            (F.count("*") - F.count_distinct(F.struct(*KEY))).alias("duplicate_key_rows"),
        )
        .first()
        .asDict()
    )
    fields = {
        field: {reason: before[f"{field}_{reason}"] for reason in ("valid", *REASONS)}
        for field in NUMERIC_FIELDS
    }
    if after["rows"] != before["rows"] - before["invalid_time_rows"] - repeated["excess_rows"]:
        raise RuntimeError("Unexpected row accounting after validation.")
    if after["duplicate_key_rows"] or after["invalid_time_rows"]:
        raise RuntimeError("Cleaned observations violate the time key contract.")
    missing_source = {m: fields[m]["blank"] + fields[m]["nan"] for m in MEASURES}
    return {
        "provenance": provenance,
        "before": {
            "rows": before["rows"],
            "invalid_time_rows": before["invalid_time_rows"],
            "incomplete_rows": before["incomplete_rows"],
            "source_missing_by_measure": missing_source,
            "exact_duplicate_source_rows_beyond_first": raw_repeats,
            "repeated_valid_keys": repeated,
            "field_status_counts": fields,
        },
        "actions": {
            "invalid_time_rows_dropped": before["invalid_time_rows"],
            "duplicate_key_rows_dropped": repeated["excess_rows"],
            "invalid_measure_cells_marked_missing_before_row_removals": {
                m: sum(fields[m][status] for status in ("malformed", "nonfinite", "out_of_range"))
                for m in MEASURES
            },
            "imputed_cells": 0,
        },
        "after": {
            "rows": after["rows"],
            "invalid_time_rows": after["invalid_time_rows"],
            "incomplete_rows": after["incomplete_rows"],
            "duplicate_key_rows": after["duplicate_key_rows"],
            "missing_by_measure": {m: after[m] for m in MEASURES},
        },
    }


def time_coverage(joined: DataFrame) -> DataFrame:
    """Inspect elapsed-time gaps against each recording's reported numeric cadence."""
    ordered = Window.partitionBy("recording_id").orderBy("time_s")
    interval = F.col("time_s") - F.lag("time_s").over(ordered)
    return (
        joined.withColumn("observed_step_s", interval)
        .withColumn("expected_step_s", 1.0 / F.col("numerics_sampling_hz"))
        .groupBy("recording_id", "expected_step_s")
        .agg(
            F.min("time_s").alias("first_time_s"),
            F.max("time_s").alias("last_time_s"),
            F.max("observed_step_s").alias("max_observed_step_s"),
            F.count_if(
                F.col("observed_step_s") > F.col("expected_step_s") + CADENCE_TOLERANCE_SECONDS
            ).alias("long_intervals"),
            F.count_if(
                F.col("observed_step_s") < F.col("expected_step_s") - CADENCE_TOLERANCE_SECONDS
            ).alias("short_intervals"),
        )
        .orderBy("recording_id")
    )
