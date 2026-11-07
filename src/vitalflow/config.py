"""Project paths and experiment defaults."""

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_VERSION = "1.0.0"
DATASET_PAGE = f"https://physionet.org/content/bidmc/{DATASET_VERSION}/"
SOURCE_BASE = f"https://physionet.org/files/bidmc/{DATASET_VERSION}/"
DATASET_DOI = "10.13026/C2208R"
DATASET_LICENSE = "Open Data Commons Attribution License v1.0"
MODES = {"fast": 3, "default": 10, "complete": 53}
MAX_RECORDINGS = MODES["complete"]
MASTER = "local[2]"
SHUFFLE_PARTITIONS = 4
WINDOW_SECONDS = 60
REPLAY_WINDOW_SECONDS = 120
REPLAY_INTERVAL_SECONDS = 1.0
BENCHMARK_TRIALS = 3


class VitalFlowError(Exception):
    """An expected acquisition, data contract or pipeline error."""


@dataclass(frozen=True)
class Project:
    root: Path = PROJECT_ROOT

    @property
    def raw(self) -> Path:
        return self.root / "data" / "raw" / "bidmc" / DATASET_VERSION

    @property
    def outputs(self) -> Path:
        return self.root / "outputs"

    def result(self, count: int) -> Path:
        return self.outputs / f"{count:02d}-recordings"


def recording_ids(count: int) -> list[str]:
    if not 1 <= count <= MAX_RECORDINGS:
        raise VitalFlowError(f"Recording count must be between 1 and {MAX_RECORDINGS}.")
    return [f"bidmc_{i:02d}" for i in range(1, count + 1)]
