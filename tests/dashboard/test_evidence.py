import json
import shutil
from statistics import median

import pytest

from vitalflow.config import Project

pytest.importorskip("streamlit")
pytest.importorskip("pyarrow")

from vitalflow.dashboard.evidence import (  # noqa: E402
    FIXTURE,
    PARQUET,
    RECORDINGS,
    RUN,
    EvidenceError,
    EvidenceRepository,
)


@pytest.mark.parametrize(
    ("mode", "count", "source_rows"),
    [
        ("fast", 3, 9),
        ("default", 10, 30),
        ("complete", 53, 160),
    ],
)
def test_snapshot_modes_and_kpis_reconcile(dashboard_project, mode, count, source_rows):
    snapshot = EvidenceRepository(dashboard_project).load(mode)
    m = snapshot.metrics
    assert m.recordings == count
    assert m.source_rows == source_rows
    assert m.retained == count * 3
    assert m.expected_cells == count * 3 * 4
    missing = 2 * count + (mode == "complete")
    assert m.missing == missing
    assert m.completeness == pytest.approx((m.expected_cells - missing) / m.expected_cells)
    assert m.median_arrival_ms == median(
        b["arrival_to_completion_ms"] for b in snapshot.velocity["batches"]
    )
    assert m.median_processing_ms == median(
        b["spark_ingest_and_process_ms"] for b in snapshot.velocity["batches"]
    )


def test_missing_mode_has_no_fallback(tmp_path):
    repository = EvidenceRepository(Project(tmp_path))
    with pytest.raises(EvidenceError, match=r"run.json: berkas tidak ditemukan"):
        repository.load("complete")
    with pytest.raises(EvidenceError, match="mode dataset tidak didukung"):
        repository.load("wrong")


@pytest.mark.parametrize(
    ("file", "contents", "error"),
    [
        (RUN, "{broken", "tidak dapat dibaca sebagai JSON"),
        (RUN, "[]", "struktur objek tidak sesuai"),
        (RECORDINGS, "", "CSV kosong"),
        (RECORDINGS, "recording_id,rows\nbidmc_01,3\n", "kolom wajib tidak ada"),
    ],
)
def test_invalid_artifacts_are_reported_by_relative_path(
    dashboard_project, tmp_path, file, contents, error
):
    project = Project(tmp_path)
    root = project.result(3)
    shutil.copytree(dashboard_project.result(3), root)
    (root / file).write_text(contents)
    with pytest.raises(EvidenceError, match=error) as info:
        EvidenceRepository(project).load("fast")
    assert info.value.artifact == file
    assert str(tmp_path) not in str(info.value)


def test_fixture_cannot_be_labeled_as_source(dashboard_project, tmp_path):
    project = Project(tmp_path)
    root = project.result(3)
    shutil.copytree(dashboard_project.result(3), root)
    (root / FIXTURE).write_bytes((root / "quality/source.json").read_bytes())
    with pytest.raises(EvidenceError, match="provenance skenario tidak sesuai"):
        EvidenceRepository(project).load("fast")


def test_revision_changes_and_missing_parquet_leaves_summary_available(dashboard_project, tmp_path):
    project = Project(tmp_path)
    root = project.result(3)
    shutil.copytree(dashboard_project.result(3), root)
    repo = EvidenceRepository(project)
    first = repo.load("fast")
    marker = json.loads((root / RUN).read_text())
    marker["elapsed_seconds"] = 11.123
    stage = root / "new-marker.json"
    stage.write_text(json.dumps(marker))
    stage.replace(root / RUN)
    assert repo.revision("fast") != first.revision
    with pytest.raises(EvidenceError, match="run baru sedang dipublikasikan"):
        repo.load("fast", first.revision)
    shutil.rmtree(root / PARQUET)
    assert repo.load("fast").run["elapsed_seconds"] == 11.123
    with pytest.raises(EvidenceError, match="Parquet tidak tersedia"):
        repo.revision("fast", detail=True)


def test_parquet_reads_only_selected_recording(dashboard_project):
    repo = EvidenceRepository(dashboard_project)
    revision = repo.revision("complete", detail=True)
    frame = repo.recording("complete", "bidmc_13", 3, revision)
    assert frame["recording_id"].unique().tolist() == ["bidmc_13"]
    assert frame["time_s"].tolist() == [0, 1, 120]
    assert frame["resp"].isna().tolist() == [False, False, True]
    with pytest.raises(EvidenceError, match="recording_id tidak ada"):
        repo.recording("fast", "bidmc_13", 3, repo.revision("fast", detail=True))
