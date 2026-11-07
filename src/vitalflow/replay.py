"""Simulate local file arrivals independently of the Spark consumer."""

import csv
import io
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from queue import Queue
from tempfile import TemporaryDirectory
from threading import Event

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from .config import REPLAY_WINDOW_SECONDS, VitalFlowError
from .quality import classify_rows
from .source import MEASURES, NUMBER, NUMERIC_FIELDS, SourceRecord, decode_source, normalize_header
from .spark import REPLAY_COLUMNS, csv_strings

DECIMAL = re.compile(NUMBER)


@dataclass(frozen=True)
class Batch:
    index: int
    source_window_start_s: int | None
    rows: int
    file: Path


@dataclass(frozen=True)
class Arrival:
    batch: Batch
    tick: float
    scheduled: float
    utc: str
    inbox_file: Path


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def stage_batches(records: list[SourceRecord], staging: Path) -> list[Batch]:
    """Stage a bounded dataset (up to 53 short recordings) without altering source files."""
    grouped: dict[int | None, list[list[str]]] = {}
    for record in records:
        reader = csv.reader(
            io.StringIO(decode_source(record.numerics.read_bytes(), record.numerics.name))
        )
        fields = normalize_header(next(reader))
        for row in reader:
            if not row:
                continue
            values = dict(zip(fields, row, strict=True))
            value = values["time_s"].strip()
            seconds = float(value) if DECIMAL.fullmatch(value) else math.nan
            window = (
                math.floor(seconds / REPLAY_WINDOW_SECONDS) * REPLAY_WINDOW_SECONDS
                if math.isfinite(seconds) and seconds >= 0
                else None
            )
            grouped.setdefault(window, []).append(
                [record.recording_id, *(values[field] for field in NUMERIC_FIELDS)]
            )
    keys = sorted(grouped, key=lambda key: (key is None, key or 0))
    batches = []
    for index, window in enumerate(keys, start=1):
        path = staging / f"batch-{index:02d}.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(REPLAY_COLUMNS)
            writer.writerows(grouped[window])
        batches.append(Batch(index, window, len(grouped[window]), path))
    return batches


def publish(
    batches: list[Batch], inbox: Path, interval_s: float, arrivals: Queue, stop: Event
) -> None:
    start = time.perf_counter()
    try:
        for index, batch in enumerate(batches):
            due = start + index * interval_s
            if stop.wait(max(0, due - time.perf_counter())):
                return
            delivered = inbox / batch.file.name
            batch.file.rename(delivered)
            arrivals.put(Arrival(batch, time.perf_counter(), due, utc_now(), delivered))
    except Exception as exc:
        arrivals.put(exc)


def replay(spark: SparkSession, records: list[SourceRecord], interval_s: float) -> dict:
    timings: list[dict] = []
    with TemporaryDirectory(prefix="vitalflow-replay-") as temp:
        root = Path(temp)
        inbox = root / "inbox"
        inbox.mkdir()
        batches = stage_batches(records, root)
        arrivals: Queue[Arrival | Exception] = Queue()
        stop = Event()
        previous: float | None = None
        with ThreadPoolExecutor(max_workers=1) as pool:
            delivery = pool.submit(publish, batches, inbox, interval_s, arrivals, stop)
            try:
                for _ in batches:
                    arrival = arrivals.get()
                    if isinstance(arrival, Exception):
                        raise VitalFlowError(f"Replay producer failed: {arrival}") from arrival
                    start = time.perf_counter()
                    started_at = utc_now()
                    incoming = csv_strings(spark, [arrival.inbox_file], REPLAY_COLUMNS)
                    stats = (
                        classify_rows(incoming)
                        .agg(
                            F.count("*").alias("processed_rows"),
                            F.count("time_s").alias("valid_time_rows"),
                            *(F.count(field).alias(f"{field}_valid") for field in MEASURES),
                        )
                        .first()
                        .asDict()
                    )
                    end = time.perf_counter()
                    if stats["processed_rows"] != arrival.batch.rows:
                        raise VitalFlowError(f"Replay lost rows in batch {arrival.batch.index}.")
                    timings.append(
                        {
                            "batch": arrival.batch.index,
                            "source_window_start_s": arrival.batch.source_window_start_s,
                            "source_window_end_s_exclusive": (
                                arrival.batch.source_window_start_s + REPLAY_WINDOW_SECONDS
                                if arrival.batch.source_window_start_s is not None
                                else None
                            ),
                            "arrived_at_utc": arrival.utc,
                            "processing_started_at_utc": started_at,
                            "completed_at_utc": utc_now(),
                            "arrival_interval_ms": (
                                round((arrival.tick - previous) * 1000, 3)
                                if previous is not None
                                else None
                            ),
                            "arrival_schedule_delay_ms": round(
                                (arrival.tick - arrival.scheduled) * 1000, 3
                            ),
                            "queue_wait_ms": round((start - arrival.tick) * 1000, 3),
                            "spark_ingest_and_process_ms": round((end - start) * 1000, 3),
                            "arrival_to_completion_ms": round((end - arrival.tick) * 1000, 3),
                            **stats,
                        }
                    )
                    previous = arrival.tick
            finally:
                stop.set()
            delivery.result()
    return {
        "provenance": "historical_bidmc_local_timed_replay",
        "target_arrival_interval_s": interval_s,
        "source_window_seconds": REPLAY_WINDOW_SECONDS,
        "elapsed_times": "Monotonic clock; UTC timestamps record wall-clock events.",
        "processing_scope": "Read incoming CSV in Spark, validate fields and materialize counts.",
        "total_processed_rows": sum(row["processed_rows"] for row in timings),
        "total_valid_time_rows": sum(row["valid_time_rows"] for row in timings),
        "batches": timings,
    }
