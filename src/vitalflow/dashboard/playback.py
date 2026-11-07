"""Streamlit playback of previously measured local arrivals."""

from time import monotonic

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .design import AMBER, CYAN, TEAL, fmt, panel_head, plot, table
from .evidence import Snapshot
from .replay import Replay, schedule_for

KEY = "vf_replay"
LABELS = {
    "batch": "Batch",
    "processed_rows": "Baris",
    "valid_time_rows": "Waktu valid",
    "arrival_interval_ms": "Interval (ms)",
    "spark_ingest_and_process_ms": "Proses Spark (ms)",
    "queue_wait_ms": "Antrean (ms)",
    "arrival_to_completion_ms": "Total latensi (ms)",
    "throughput": "Baris/detik",
    "arrived_at_utc": "Tiba (UTC)",
    "processing_started_at_utc": "Mulai (UTC)",
    "completed_at_utc": "Selesai (UTC)",
    "source_window": "Jendela rekaman",
}


def playback(snapshot: Snapshot) -> None:
    value = snapshot.velocity
    batches = value["batches"]
    schedule = schedule_for(batches)
    if KEY not in st.session_state:
        st.session_state[KEY] = Replay()

    def change(command: str) -> None:
        current = st.session_state[KEY]
        st.session_state[KEY] = {
            "start": lambda: current.start(schedule, monotonic()),
            "pause": lambda: current.pause(schedule, monotonic()),
            "reset": Replay,
            "step": lambda: current.step(schedule, monotonic()),
        }[command]()
        st.rerun()

    @st.fragment(run_every=0.25 if st.session_state[KEY].running else None)
    def player() -> None:
        previous = st.session_state[KEY]
        cursor = previous.tick(schedule, monotonic())
        st.session_state[KEY] = cursor
        if previous.running and not cursor.running:
            st.rerun()
        complete = cursor.visible == len(batches)
        with st.container(border=True, key="panel_replay"):
            panel_head(
                "Historical Dataset Replay — Simulated IoT Ingestion",
                f"Target: {fmt(value['target_arrival_interval_s'], 2)} detik antarbatch · "
                f"{fmt(value['source_window_seconds'])} detik data rekaman per jendela",
            )
            a, b, c, d = st.columns(4)
            if a.button(
                "Mulai replay",
                type="primary",
                disabled=cursor.running or complete,
                key="replay_start",
                width="stretch",
            ):
                change("start")
            if b.button("Jeda", disabled=not cursor.running, key="replay_pause", width="stretch"):
                change("pause")
            if c.button("Reset", disabled=cursor.visible == 0, key="replay_reset", width="stretch"):
                change("reset")
            if d.button(
                "Langkah berikutnya",
                disabled=complete or cursor.running,
                key="replay_step",
                width="stretch",
            ):
                change("step")
            status = (
                "Selesai"
                if complete
                else "Diputar"
                if cursor.running
                else "Dijeda"
                if cursor.visible
                else "Siap"
            )
            st.progress(
                cursor.visible / len(batches),
                text=f"{status} · {cursor.visible} / {len(batches)} batch",
            )
        if not cursor.visible:
            st.info(
                "Mulai replay untuk mengikuti interval kedatangan terukur, atau tampilkan batch satu per satu."
            )
            return
        rows = []
        for batch in batches[: cursor.visible]:
            elapsed = batch["spark_ingest_and_process_ms"]
            start = batch["source_window_start_s"]
            rows.append(
                {
                    **batch,
                    "throughput": round(1000 * batch["processed_rows"] / elapsed, 2)
                    if elapsed > 0
                    else None,
                    "source_window": (
                        f"[{start}, {batch['source_window_end_s_exclusive']}) detik"
                        if start is not None
                        else "Timestamp tidak valid"
                    ),
                }
            )
        last = rows[-1]
        for col, (label, display) in zip(
            st.columns(4),
            (
                ("Baris diproses", fmt(sum(r["processed_rows"] for r in rows))),
                (
                    "Interval terukur",
                    f"{fmt(last['arrival_interval_ms'], 1)} ms"
                    if last["arrival_interval_ms"] is not None
                    else "—",
                ),
                ("Proses Spark", f"{fmt(last['spark_ingest_and_process_ms'], 1)} ms"),
                (
                    "Throughput batch",
                    f"{fmt(last['throughput'], 1)} baris/s"
                    if last["throughput"] is not None
                    else "—",
                ),
            ),
            strict=True,
        ):
            col.metric(label, display)
        a, b = st.columns(2)
        positions = [row["batch"] for row in rows]
        with a:
            panel_head("Baris per batch")
            fig = go.Figure(
                go.Bar(
                    x=positions,
                    y=[r["processed_rows"] for r in rows],
                    marker_color=CYAN,
                    hovertemplate="Batch %{x} · %{y} baris<extra></extra>",
                )
            )
            fig.update_xaxes(title="Batch", dtick=1)
            fig.update_yaxes(title="Baris", rangemode="tozero")
            plot(fig, "replay-rows", 215)
        with b:
            panel_head("Rincian latensi")
            fig = go.Figure()
            for key, name, color in (
                ("spark_ingest_and_process_ms", "Proses Spark", CYAN),
                ("queue_wait_ms", "Antrean", AMBER),
                ("arrival_to_completion_ms", "Tiba → selesai", TEAL),
            ):
                fig.add_scatter(
                    x=positions,
                    y=[r[key] for r in rows],
                    name=name,
                    mode="lines+markers",
                    line={"color": color},
                    hovertemplate="%{y:.1f} ms",
                )
            fig.update_xaxes(title="Batch", dtick=1)
            fig.update_yaxes(title="Durasi (ms)", rangemode="tozero")
            plot(fig, "replay-latency", 215, legend=True)
        with st.expander("Log batch · timestamp asli dalam UTC"):
            table(
                pd.DataFrame(rows)[list(LABELS)].rename(columns=LABELS),
                key="replay_log",
                height=220,
            )
            st.caption(
                "Throughput = jumlah baris batch ÷ waktu baca, validasi, dan penghitungan Spark. "
                "Interval pertama tidak tersedia karena belum ada batch sebelumnya."
            )

    player()
