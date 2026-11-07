"""Stage generated results and publish complete local snapshots."""

import csv
import fcntl
import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from .config import Project, VitalFlowError

RUN_FORMAT = "vitalflow-iteration-01"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise VitalFlowError(f"No rows to export for {path.name}.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def check_existing(destination: Path, count: int) -> None:
    if not destination.exists() and not destination.is_symlink():
        return
    try:
        marker = destination / "run.json"
        if destination.is_symlink() or marker.is_symlink():
            raise ValueError("symlink")
        data = json.loads(marker.read_text(encoding="utf-8"))
        if data["format"] == RUN_FORMAT and data["recording_count"] == count:
            return
    except (OSError, ValueError, KeyError, TypeError):
        pass
    raise VitalFlowError(f"Refusing to replace an unmanaged result path: {destination}")


@contextmanager
def staged_result(project: Project, count: int) -> Iterator[Path]:
    if project.outputs.is_symlink():
        raise VitalFlowError("Refusing to write through a symlinked outputs directory.")
    project.outputs.mkdir(parents=True, exist_ok=True)
    destination = project.result(count)
    with (project.outputs / f".{destination.name}.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise VitalFlowError(f"A run is already publishing {destination.name}.") from exc
        check_existing(destination, count)
        with TemporaryDirectory(prefix=".staging-", dir=project.outputs) as temp:
            workspace = Path(temp)
            stage = workspace / "result"
            previous = workspace / "previous"
            stage.mkdir()
            yield stage
            check_existing(stage, count)
            if destination.exists():
                destination.rename(previous)
            try:
                stage.rename(destination)
            except OSError:
                if previous.exists():
                    previous.rename(destination)
                raise
