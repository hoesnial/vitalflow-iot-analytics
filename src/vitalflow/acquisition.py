"""Incremental, checksum-verified downloads with an immutable source cache."""

import hashlib
import logging
import os
import re
import tempfile
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .config import (
    DATASET_DOI,
    DATASET_LICENSE,
    DATASET_PAGE,
    DATASET_VERSION,
    SOURCE_BASE,
    Project,
    VitalFlowError,
    recording_ids,
)
from .source import SourceRecord, decode_source, inspect_csv, parse_fix

LOG = logging.getLogger(__name__)
CHECKSUM_FILE = "SHA256SUMS.txt"
ATTEMPTS = 3
TIMEOUT_SECONDS = 20
MAX_DOWNLOAD_BYTES = 1_048_576  # Scope is numerics, Fix.txt and the official checksum list.
DOWNLOAD_WORKERS = 6


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_checksums(data: bytes) -> dict[str, str]:
    checksums = {}
    for line in decode_source(data, CHECKSUM_FILE).splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?([^\s]+)", line)
        if not match or match[2] in checksums:
            raise VitalFlowError(f"{CHECKSUM_FILE}: malformed or repeated checksum entry.")
        checksums[match[2]] = match[1].lower()
    return checksums


def fetch(url: str, validate: Callable[[bytes], object]) -> bytes:
    for attempt in range(1, ATTEMPTS + 1):
        try:
            request = Request(
                url, headers={"User-Agent": "VitalFlow/0.1 (academic dataset client)"}
            )
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                if response.headers.get_content_type() in {"text/html", "application/xhtml+xml"}:
                    raise VitalFlowError("Received an HTML response.")
                data = response.read(MAX_DOWNLOAD_BYTES + 1)
            if len(data) > MAX_DOWNLOAD_BYTES:
                raise VitalFlowError("Response exceeded the expected size limit.")
            validate(data)
            return data
        except (HTTPException, OSError, VitalFlowError) as exc:
            permanent = (
                isinstance(exc, HTTPError) and 400 <= exc.code < 500 and exc.code not in {408, 429}
            )
            if permanent or attempt == ATTEMPTS:
                raise VitalFlowError(f"{url}: failed after {attempt} attempt(s): {exc}") from exc
            LOG.warning("Retry %d/%d for %s: %s", attempt + 1, ATTEMPTS, url, exc)
            time.sleep(0.5 * 2 ** (attempt - 1))
    raise AssertionError("retry loop exhausted")


def cache_file(
    path: Path, url: str, validate: Callable[[bytes], object], *, offline: bool
) -> tuple[bytes, str]:
    def read_cached() -> tuple[bytes, str]:
        data = path.read_bytes()
        try:
            validate(data)
        except VitalFlowError as exc:
            raise VitalFlowError(
                f"Invalid cache file {path}: {exc} Move it out of the raw cache and retry."
            ) from exc
        return data, "cached"

    if path.is_file():
        return read_cached()
    if offline:
        raise VitalFlowError(
            f"Missing cached {path.name}. Run vitalflow download for this selection."
        )
    data = fetch(url, validate)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Hard-link publication is atomic and cannot overwrite an existing raw file.
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".download-") as staging:
        staging.write(data)
        staging.flush()
        os.fsync(staging.fileno())
        try:
            os.link(staging.name, path)
        except FileExistsError:
            return read_cached()
    return data, "downloaded"


def acquire(project: Project, count: int, *, offline: bool) -> tuple[list[SourceRecord], dict]:
    ids = recording_ids(count)
    checksum_url = f"{SOURCE_BASE}{CHECKSUM_FILE}"

    def selected_checksums(data: bytes) -> dict[str, str]:
        result = parse_checksums(data)
        expected = {
            f"bidmc_csv/{rid}_{suffix}" for rid in ids for suffix in ("Numerics.csv", "Fix.txt")
        }
        if missing := expected - result.keys():
            raise VitalFlowError(f"{CHECKSUM_FILE}: missing entries {sorted(missing)}.")
        return result

    checksum_bytes, checksum_status = cache_file(
        project.raw / CHECKSUM_FILE, checksum_url, selected_checksums, offline=offline
    )
    checksums = selected_checksums(checksum_bytes)

    def get_record(recording_id: str) -> tuple[SourceRecord, list[dict]]:
        files = []
        for suffix in ("Numerics.csv", "Fix.txt"):
            relative = f"bidmc_csv/{recording_id}_{suffix}"
            url, path, digest = (
                f"{SOURCE_BASE}{relative}",
                project.raw / relative,
                checksums[relative],
            )

            def validate(data: bytes) -> None:
                if sha256(data) != digest:
                    raise VitalFlowError(f"{path.name}: SHA-256 differs from PhysioNet's checksum.")
                if suffix == "Numerics.csv":
                    inspect_csv(data, path.name)
                else:
                    parse_fix(data, recording_id)

            data, status = cache_file(path, url, validate, offline=offline)
            files.append(
                {
                    "recording_id": recording_id,
                    "relative_path": relative,
                    "url": url,
                    "bytes": len(data),
                    "sha256": digest,
                    "status": status,
                }
            )
        return SourceRecord(
            recording_id,
            project.raw / files[0]["relative_path"],
            project.raw / files[1]["relative_path"],
        ), files

    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
        results = list(pool.map(get_record, ids))
    manifest = {
        "dataset": "BIDMC PPG and Respiration Dataset",
        "version": DATASET_VERSION,
        "dataset_page": DATASET_PAGE,
        "doi": DATASET_DOI,
        "license": DATASET_LICENSE,
        "checksum_manifest": {
            "url": checksum_url,
            "sha256": sha256(checksum_bytes),
            "status": checksum_status,
        },
        "files": [file for _, files in results for file in files],
    }
    return [record for record, _ in results], manifest
