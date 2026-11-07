"""Overview and the per-recording data explorer."""

from datetime import timedelta, timezone
from html import escape

import streamlit as st

from vitalflow.source import MEASURES

from .analysis import CHANNELS, filter_recording, observed_stats
from .charts import missing_bars, raw_trend, window_trend
from .design import fmt, page_head, panel_head, plot, strip, table
from .evidence import Snapshot, stamp

WIB = timezone(timedelta(hours=7), "WIB")
V_NAMES = ("Volume", "Velocity", "Variety", "Veracity", "Value")
V_LINES = (
    "Bandingkan agregasi sederhana dengan join dan pengelompokan waktu.",
    "Putar ulang batch historis dan periksa waktu kedatangan serta prosesnya.",
    "Lihat bagaimana Spark menggabungkan CSV dengan JSON.",
    "Telusuri nilai hilang, timestamp invalid, dan aturan validasi.",
    "Baca tren fisiologis bersama jumlah pengukuran yang mendukungnya.",
)


def open_lab(name: str) -> None:
    st.session_state["vf_page"] = "Big Data 5Vs Lab"
    st.session_state["vf_lab"] = name


def overview(snapshot: Snapshot) -> None:
    st.html("""
        <header class="vf-head vf-hero">
          <div class="vf-hero-meta"><div class="vf-label">IFB-451 · LABORATORIUM DATA</div>
          <div class="vf-tagline">From Raw Patient Monitoring Data to Meaningful Insights</div></div>
          <h1>VitalFlow</h1>
          <strong>IoT Patient Monitoring &amp; Big Data Analytics</strong>
          <p>Analisis data tanda vital menggunakan Apache Spark</p>
          <div class="vf-badges">
            <span class="vf-badge vf-badge--source">PhysioNet BIDMC — Historical Hospital Data</span>
            <span class="vf-badge vf-badge--replay">Simulated IoT Replay • Educational Prototype</span>
          </div>
        </header>
    """)
    m = snapshot.metrics
    items = (
        ("Rekaman", fmt(m.recordings), "Recording ID resmi pada snapshot terpilih."),
        (
            "Observasi tersimpan",
            fmt(m.retained),
            "Baris setelah validasi, diverifikasi kembali dari Parquet.",
        ),
        (
            "Kelengkapan data",
            f"{fmt(m.completeness * 100, 2)}%",
            f"{fmt(m.expected_cells - m.missing)} dari {fmt(m.expected_cells)} sel kanal tersimpan berisi nilai.",
        ),
        (
            "Median latensi replay",
            f"{fmt(m.median_arrival_ms, 1)} ms",
            "Waktu dari batch tiba di inbox lokal hingga Spark selesai. Diukur saat eksperimen replay.",
        ),
    )
    for col, (label, value, help_text) in zip(st.columns(4), items, strict=True):
        col.metric(label, value, help=help_text)
    main, side = st.columns([1.78, 1], vertical_alignment="top")
    with main, st.container(border=True, key="panel_trend"):
        rid = snapshot.ids[0]
        panel_head(
            "Tren fisiologis",
            f"{rid} · rata-rata per jendela {snapshot.run['analytics_window_seconds']} detik",
        )
        channel = st.radio(
            "Kanal tren",
            MEASURES,
            format_func=lambda k: CHANNELS[k].label,
            horizontal=True,
            key="preview_channel",
            label_visibility="collapsed",
        )
        frame = snapshot.windows[snapshot.windows["recording_id"] == rid]
        plot(
            window_trend(frame, channel, snapshot.run["analytics_window_seconds"]),
            "overview-trend",
            220,
        )
        st.caption("Arahkan kursor untuk melihat rata-rata dan jumlah bacaan valid.")
    with side, st.container(border=True, key="panel_quality"):
        panel_head(
            "Kelengkapan kanal", f"{fmt(m.missing)} sel kosong setelah validasi · tidak diimputasi"
        )
        plot(missing_bars(snapshot.run["clean_missing_by_measure"]), "overview-missing", 185)
        last = (
            stamp(snapshot.run["completed_at_utc"]).astimezone(WIB).strftime("%d/%m/%Y · %H:%M WIB")
        )
        source = escape(snapshot.provenance["version"])
        st.html(f"""<div class="vf-ledger">
          <span><strong>✓ Pipeline terverifikasi</strong> · CSV/JSON → Parquet → Spark SQL</span>
          <span>BIDMC v{source} · {fmt(snapshot.run["source_files"])} berkas sumber</span>
          <span>Run terakhir · {escape(last)}</span>
        </div>""")
    st.subheader("Pertanyaan yang Dijawab VitalFlow")
    strip(
        "Bagaimana tanda vital dan ketersediaan pengukurannya berubah sepanjang rekaman? "
        "Bandingkan nilai dan kelengkapan sebelum menafsirkan sebuah tren."
    )
    st.subheader("Jelajahi 5Vs")
    for col, (idx, name, desc) in zip(
        st.columns(5), zip(range(1, 6), V_NAMES, V_LINES, strict=True), strict=True
    ):
        with col:
            st.html(
                f'<div class="vf-vitem"><div class="vf-label">0{idx} / 05</div>'
                f"<strong>{name}</strong><p>{escape(desc)}</p></div>"
            )
            st.button(
                f"Buka {name}", key=f"open_{name}", on_click=open_lab, args=(name,), width="stretch"
            )


def reset_filters(generation_key: str) -> None:
    # New widget IDs discard pending browser values from the previous filter set.
    st.session_state[generation_key] = st.session_state.get(generation_key, 0) + 1


def explorer(snapshot: Snapshot, read_recording) -> None:
    page_head(
        "02 / REKAMAN",
        "Recording Explorer",
        "Amati tanda vital dari rekaman historis pada interval yang Anda pilih.",
    )
    generation_key = f"vf_explorer_generation_{snapshot.mode}"
    generation = st.session_state.get(generation_key, 0)
    prefix = f"explorer_{snapshot.mode}_"
    if generation:
        prefix += f"reset_{generation}_"
    with st.container(border=True, key="panel_filters"):
        a, b, c = st.columns([1, 1, 2])
        rid = a.selectbox("Recording ID", snapshot.ids, key=prefix + "recording")
        channel = b.selectbox(
            "Kanal", MEASURES, format_func=lambda key: CHANNELS[key].label, key=prefix + "channel"
        )
        meta = snapshot.metadata[rid]
        summary = snapshot.recordings.loc[snapshot.recordings["recording_id"] == rid].iloc[0]
        cadence = 1 / meta["numerics_sampling_hz"]
        low, high = float(summary["first_time_s"]), float(summary["last_time_s"])
        if high > low:
            interval = c.slider(
                "Interval rekaman (detik)",
                low,
                high,
                (low, high),
                step=min(cadence, high - low),
                format="%.1f",
                key=f"{prefix}interval_{rid}_{low}_{high}",
            )
        else:
            interval = (low, high)
            c.caption(f"Satu waktu yang tersedia: {fmt(low, 1)} detik")
        toggle, compare, reset = st.columns([1.25, 1.5, 1], vertical_alignment="center")
        show_gaps = toggle.toggle("Tandai nilai hilang", value=True, key=prefix + "gaps")
        channels = (channel,)
        if channel in ("hr", "pulse"):
            other = "pulse" if channel == "hr" else "hr"
            if compare.toggle(
                f"Bandingkan dengan {CHANNELS[other].label}", key=prefix + "compare_" + channel
            ):
                channels += (other,)
        else:
            compare.caption("Kanal ini memakai skala tersendiri.")
        reset.button(
            "Reset filter",
            key="reset_explorer",
            on_click=reset_filters,
            args=(generation_key,),
            width="stretch",
        )
    frame = read_recording(rid, int(summary["rows"]))
    filtered = filter_recording(frame, *interval)
    if filtered.empty:
        st.info("Tidak ada observasi pada interval ini. Perluas rentang atau reset filter.")
        return
    stats = observed_stats(filtered, channels)
    with st.container(border=True, key="panel_recording"):
        panel_head(
            f"{' + '.join(CHANNELS[k].label for k in channels)} · {rid}",
            f"{CHANNELS[channel].description} · {fmt(interval[0], 1)}–{fmt(interval[1], 1)} detik",
        )
        if not stats[0]["Valid"]:
            st.warning(
                f"Tidak ada pengukuran {CHANNELS[channel].label} yang valid di interval ini."
            )
        plot(
            raw_trend(filtered, channels, cadence, markers=show_gaps),
            "recording-trend",
            310,
            legend=len(channels) > 1 or (show_gaps and any(s["Hilang"] for s in stats)),
        )
        st.caption(
            "Celah berarti nilai tidak tersedia. Tanda amber, jika aktif, menunjukkan sel kosong "
            "pada lajur terpisah; bukan nilai fisiologis."
        )
    panel_head("Statistik interval", "Dihitung dari nilai Parquet pada interval yang dipilih.")
    table(
        stats,
        key="recording_stats",
        columns={
            key: st.column_config.NumberColumn(format="%.2f")
            for key in ("Minimum", "Maksimum", "Rata-rata")
        },
    )
    with st.expander("Metadata recording · dari Fix.txt"):
        table(
            [
                {"Atribut": k, "Nilai": v}
                for k, v in {
                    "Recording ID": rid,
                    "Lokasi (kode sumber)": meta["location"],
                    "Frekuensi numerik": f"{fmt(meta['numerics_sampling_hz'], 1)} Hz",
                    "Frekuensi sinyal": f"{fmt(meta['signals_sampling_hz'], 1)} Hz",
                    "Kanal numerik": ", ".join(meta["numeric_channels"]),
                    "Versi dataset": meta["dataset_version"],
                }.items()
            ],
            key="recording_metadata",
        )
        st.markdown(f"[Lihat Fix.txt di PhysioNet]({meta['source_fix_url']})")
        st.caption("Recording ID adalah kunci rekaman. Panel ini tidak mengidentifikasi pasien.")
    with st.expander("Pengukuran pada interval ini"):
        table(
            filtered[["time_s", *channels]].rename(
                columns={"time_s": "Waktu (detik)", **{k: CHANNELS[k].label for k in channels}}
            ),
            key="recording_values",
            height=252,
        )
