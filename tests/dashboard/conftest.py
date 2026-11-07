"""Create isolated evidence snapshots with the real pipeline and synthetic source bytes."""

import shutil

import pytest

from vitalflow import acquisition
from vitalflow.acquisition import CHECKSUM_FILE, acquire, sha256
from vitalflow.config import MODES, PROJECT_ROOT, SOURCE_BASE, Project, recording_ids
from vitalflow.pipeline import RunOptions, run

FIX = """{rid}
Location: micu
Signals sampling frequency: 125 Hz
Numerics sampling frequency: 1 Hz
Numerics: HR; PULSE; RESP; SpO2
"""
HEADER = "Time [s], HR, PULSE, RESP, SpO2\n"


@pytest.fixture(scope="session")
def dashboard_project(tmp_path_factory, spark):
    pytest.importorskip("streamlit")
    pytest.importorskip("pyarrow")
    root = tmp_path_factory.mktemp("dashboard-evidence")
    project = Project(root)
    scenarios = root / "data" / "scenarios"
    scenarios.mkdir(parents=True)
    shutil.copyfile(
        PROJECT_ROOT / "data/scenarios/controlled_quality.csv", scenarios / "controlled_quality.csv"
    )
    sources = {}
    for i, rid in enumerate(recording_ids(53), start=1):
        rows = [
            f"0,{70 + i},71,17,98",
            "1,72,NaN,17,",
            "120,75,73,NaN,97" if i == 13 else "120,75,73,18,97",
        ]
        if i == 23:
            rows.insert(0, "-1,71,70,16,98")
        sources[f"bidmc_csv/{rid}_Numerics.csv"] = (HEADER + "\n".join(rows) + "\n").encode()
        sources[f"bidmc_csv/{rid}_Fix.txt"] = FIX.format(rid=rid).encode()
    sources[CHECKSUM_FILE] = "".join(
        f"{sha256(data)} {path}\n" for path, data in sources.items()
    ).encode()

    def mock_fetch(url, validate):
        data = sources[url.removeprefix(SOURCE_BASE)]
        validate(data)
        return data

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(acquisition, "fetch", mock_fetch)
        acquire(project, 53, offline=False)
    for count in MODES.values():
        run(spark, project, RunOptions(count, replay_interval_s=0.01))
    return project
