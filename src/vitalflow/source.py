"""Validate the BIDMC CSV contract and allowlist fixed recording metadata."""

import csv
import io
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .config import DATASET_VERSION, MAX_RECORDINGS, SOURCE_BASE, VitalFlowError

HEADERS = {"Time [s]": "time_s", "HR": "hr", "PULSE": "pulse", "RESP": "resp", "SpO2": "spo2"}
MEASURES = ("hr", "pulse", "resp", "spo2")
NUMERIC_FIELDS = ("time_s", *MEASURES)
NUMBER = r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
INTEGER = re.compile(r"[+-]?[0-9]+")
DECIMAL = re.compile(NUMBER)
FIX_FIELDS = {
    "Signals sampling frequency": "signals_sampling_hz",
    "Numerics sampling frequency": "numerics_sampling_hz",
    "Location": "location",
    "Numerics": "numeric_channels",
}
FREQUENCY = re.compile(rf"({NUMBER})\s*Hz", re.IGNORECASE)


@dataclass(frozen=True)
class SourceRecord:
    recording_id: str
    numerics: Path
    fix: Path


def validate_recording_id(recording_id: str) -> None:
    match = re.fullmatch(r"bidmc_([0-9]{2})", recording_id)
    if not match or not 1 <= int(match[1]) <= MAX_RECORDINGS:
        raise VitalFlowError(f"Invalid BIDMC recording ID: {recording_id!r}")


def decode_source(data: bytes, label: str) -> str:
    if not data.strip() or data.lstrip().startswith(b"<"):
        raise VitalFlowError(f"{label}: empty or HTML/XML response.")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise VitalFlowError(f"{label}: expected UTF-8 text.") from exc


def normalize_header(header: list[str]) -> tuple[str, ...]:
    normalized = [field.strip() for field in header]
    if len(normalized) != len(HEADERS) or set(normalized) != set(HEADERS):
        raise VitalFlowError(f"Unexpected BIDMC CSV header: {header!r}.")
    return tuple(HEADERS[field] for field in normalized)


def token_kind(value: str) -> str:
    value = value.strip()
    if not value:
        return "blank"
    if value.casefold() == "nan":
        return "nan"
    if INTEGER.fullmatch(value):
        return "integer"
    if DECIMAL.fullmatch(value):
        return "decimal_or_scientific"
    return "other"


def inspect_csv(data: bytes, label: str) -> dict:
    """Check every row's width and observe lexical types without coercing bad cells."""
    reader = csv.reader(io.StringIO(decode_source(data, label)), strict=True)
    try:
        header = next(reader, [])
        fields = normalize_header(header)
        kinds: dict[str, Counter] = {field: Counter() for field in fields}
        rows = 0
        for row in reader:
            if not row:  # Spark's CSV reader also skips empty lines.
                continue
            if len(row) != len(fields) or any("\n" in value or "\r" in value for value in row):
                raise VitalFlowError(f"Malformed row ending at CSV line {reader.line_num}.")
            for field, value in zip(fields, row, strict=True):
                kinds[field][token_kind(value)] += 1
            rows += 1
    except csv.Error as exc:
        raise VitalFlowError(f"{label}: malformed CSV at line {reader.line_num}: {exc}") from exc
    except VitalFlowError as exc:
        raise VitalFlowError(f"{label}: {exc}") from exc
    if not rows:
        raise VitalFlowError(f"{label}: header without observations.")
    return {"header": header, "fields": fields, "rows": rows, "lexical_types": kinds}


def parse_fix(data: bytes, recording_id: str) -> dict:
    """Derive public recording metadata; ignore demographics and upstream subject IDs."""
    validate_recording_id(recording_id)
    lines = decode_source(data, f"{recording_id} Fix.txt").splitlines()
    if not lines or lines[0].strip() != recording_id:
        raise VitalFlowError(f"{recording_id} Fix.txt: recording marker does not match filename.")
    fields: dict[str, str] = {}
    for line in lines[1:]:
        key, sep, value = line.partition(":")
        if not sep or key.strip() not in FIX_FIELDS:
            continue
        key = FIX_FIELDS[key.strip()]
        if key in fields:
            raise VitalFlowError(f"{recording_id} Fix.txt: repeated field {key}.")
        fields[key] = value.strip()
    if missing := set(FIX_FIELDS.values()) - fields.keys():
        raise VitalFlowError(f"{recording_id} Fix.txt: missing fields {sorted(missing)}.")
    channels = [part.strip() for part in fields["numeric_channels"].split(";")]
    if len(channels) != len(MEASURES) or set(channels) != set(list(HEADERS)[1:]):
        raise VitalFlowError(f"{recording_id} Fix.txt: unexpected numeric channels.")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9 _/-]*", fields["location"]):
        raise VitalFlowError(f"{recording_id} Fix.txt: malformed location.")
    result = {
        "recording_id": recording_id,
        "location": fields["location"],
        "numeric_channels": channels,
        "dataset_version": DATASET_VERSION,
        "source_fix_url": f"{SOURCE_BASE}bidmc_csv/{recording_id}_Fix.txt",
    }
    for field in ("signals_sampling_hz", "numerics_sampling_hz"):
        match = FREQUENCY.fullmatch(fields[field])
        value = float(match[1]) if match else 0.0
        if not math.isfinite(value) or value <= 0:
            raise VitalFlowError(f"{recording_id} Fix.txt: invalid {field}.")
        result[field] = value
    return result
