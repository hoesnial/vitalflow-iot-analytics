"""Dashboard shell and cache boundaries."""

import os
from pathlib import Path
from time import monotonic

import streamlit as st

from vitalflow.config import MODES, PROJECT_ROOT, Project

from .design import apply_style, brand, fmt, page_head
from .evidence import EvidenceError, EvidenceRepository, Revision, Snapshot
from .lab import lab
from .overview import explorer, overview
from .playback import KEY
from .replay import schedule_for
from .system import architecture, evidence

PAGES = (
    "Overview",
    "Recording Explorer",
    "Big Data 5Vs Lab",
    "System Architecture",
    "Evidence & Methodology",
)
ICONS = ("01", "02", "03", "04", "05")
MODES_LABEL = {key: f"{key.title()} · {count} rekaman" for key, count in MODES.items()}


@st.cache_data(max_entries=12, show_spinner=False)
def cached_snapshot(root: str, mode: str, revision: Revision) -> Snapshot:
    return EvidenceRepository(Project(Path(root))).load(mode, revision)


@st.cache_data(max_entries=24, show_spinner=False)
def cached_recording(root: str, mode: str, rid: str, rows: int, revision: Revision):
    return EvidenceRepository(Project(Path(root))).recording(mode, rid, rows, revision)


def run_index(repository: EvidenceRepository) -> list[dict]:
    result = []
    for mode in MODES:
        try:
            run = cached_snapshot(str(repository.project.root), mode, repository.revision(mode))
        except EvidenceError:
            result.append(
                {
                    "Mode": MODES_LABEL[mode],
                    "Sumber": "—",
                    "Tersimpan": "—",
                    "Bukti": "Tidak tersedia",
                }
            )
        else:
            result.append(
                {
                    "Mode": MODES_LABEL[mode],
                    "Sumber": fmt(run.metrics.source_rows),
                    "Tersimpan": fmt(run.metrics.retained),
                    "Bukti": "Tersedia",
                }
            )
    return result


def main() -> None:
    st.set_page_config(
        page_title="VitalFlow · Big Data Analytics",
        page_icon=":material/monitor_heart:",
        layout="wide",
        initial_sidebar_state="auto",
        menu_items={
            "About": "VitalFlow · IFB-451 · prototipe edukasi dengan rekaman historis BIDMC."
        },
    )
    apply_style()
    project = Project(Path(os.environ.get("VITALFLOW_PROJECT_ROOT", str(PROJECT_ROOT))).resolve())
    repository = EvidenceRepository(project)
    with st.sidebar:
        brand()
        st.html('<div class="vf-label">Navigasi</div>')
        page = st.radio(
            "Navigasi",
            PAGES,
            format_func=lambda name: f"{ICONS[PAGES.index(name)]}  {name}",
            key="vf_page",
            label_visibility="collapsed",
        )
        st.divider()
        st.html('<div class="vf-label">Snapshot data</div>')
        mode = st.selectbox(
            "Mode dataset",
            tuple(MODES),
            index=2,
            format_func=MODES_LABEL.get,
            key="vf_mode",
            label_visibility="collapsed",
        )
        st.caption("Mode menentukan sumber seluruh angka dan grafik.")
        st.divider()
        st.html(
            '<div class="vf-meta"><strong>IFB-451 · Itenas</strong><br>Data historis · prototipe edukasi</div>'
        )
    try:
        revision = repository.revision(mode)
        snapshot = cached_snapshot(str(project.root), mode, revision)
    except EvidenceError as exc:
        st.session_state.pop(KEY, None)
        page_head(
            "SNAPSHOT TIDAK TERSEDIA", "Bukti belum siap", f"Mode terpilih: {MODES_LABEL[mode]}."
        )
        st.error(f"{exc.artifact}: {exc.reason}.")
        st.write(
            "Buat ulang mode ini dari direktori VitalFlow, lalu muat ulang halaman. "
            "Jika cache sudah lengkap, perintah download dapat dilewati."
        )
        st.code(f"vitalflow download --mode {mode}\nvitalflow run --mode {mode}", language="bash")
        return
    identity = (mode, revision)
    if st.session_state.get("vf_identity") != identity:
        st.session_state.pop(KEY, None)
        st.session_state["vf_identity"] = identity
    elif KEY in st.session_state and not (
        page == "Big Data 5Vs Lab" and st.session_state.get("vf_lab") == "Velocity"
    ):
        replay = st.session_state[KEY]
        if replay.running:
            st.session_state[KEY] = replay.pause(
                schedule_for(snapshot.velocity["batches"]), monotonic()
            )

    if page == "Overview":
        overview(snapshot)
    elif page == "Recording Explorer":

        def read_recording(rid: str, count: int):
            detail_revision = repository.revision(mode, detail=True)
            if detail_revision[: len(revision)] != revision:
                raise EvidenceError("run.json", "run baru sedang dipublikasikan; muat ulang")
            return cached_recording(str(project.root), mode, rid, count, detail_revision)

        try:
            explorer(snapshot, read_recording)
        except EvidenceError as exc:
            st.error(
                f"{exc.artifact}: {exc.reason}. Ringkasan masih dapat dibuka pada halaman Overview."
            )
            st.code(f"vitalflow run --mode {mode}", language="bash")
    elif page == "Big Data 5Vs Lab":
        lab(
            snapshot,
            repository,
            run_index(repository) if st.session_state.get("vf_lab", "Volume") == "Volume" else [],
        )
    elif page == "System Architecture":
        architecture()
    elif page == "Evidence & Methodology":
        evidence(snapshot, repository)
