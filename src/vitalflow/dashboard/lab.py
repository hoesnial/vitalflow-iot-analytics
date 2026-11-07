"""Five evidence views, with module mappings and interpretation."""

import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from vitalflow.source import MEASURES

from .analysis import (
    CHANNELS,
    clean_missing_by_recording,
    complete_minute_pair,
    source_missing_by_recording,
)
from .charts import missing_bars, recording_bars, window_trend
from .design import CYAN, TEAL, fmt, page_head, panel_head, plot, strip, table
from .evidence import (
    KEY_CHECKS,
    PLANS,
    RECORDINGS,
    WINDOWS,
    EvidenceRepository,
    Snapshot,
)
from .overview import V_NAMES
from .playback import playback

OP_LABELS = {"aggregation": "A · Group/count", "join_and_window": "B · Join + jendela"}
V_DETAILS = {
    "Volume": (
        "M1 · M2 · M5 · M6",
        "Jumlah data dan hubungan antartabel menentukan jenis kerja Spark.",
        "Dataset numerik ini kecil. Hasil lokal tidak membuktikan performa terdistribusi atau keunggulan universal.",
    ),
    "Velocity": (
        "M1 · M2 · M5 · M6",
        "Seberapa sering data tiba, berapa lama menunggu, dan kapan pemrosesan selesai?",
        "Ini pemutaran ulang log eksperimen lokal. Waktu yang ditampilkan bukan latensi sensor ke rumah sakit.",
    ),
    "Variety": (
        "M3 · M4",
        "Data dengan format dan struktur berbeda dapat dihubungkan melalui satu kunci yang teruji.",
        "JSON berasal dari Fix.txt untuk rekaman yang sama. Tidak ada identitas pasien atau sumber klinis tambahan.",
    ),
    "Veracity": (
        "M3 · M4 · M7",
        "Sebuah nilai hanya berguna bila batasan kualitasnya diketahui.",
        "Aturan format bukan ambang klinis. Nilai kosong tetap null; hasil fixture sintetis tidak berlaku pada sumber.",
    ),
    "Value": (
        "M7",
        "Tren menjadi berguna jika dibaca bersama jumlah pengukuran yang mendukungnya.",
        "Rekaman historis dan observasional. Data hilang membatasi penafsiran; tidak ada diagnosis, penggunaan klinis, atau generalisasi pasien.",
    ),
}


def lab(snapshot: Snapshot, repository: EvidenceRepository, run_index: list[dict]) -> None:
    page_head(
        "03 / 5Vs",
        "Big Data 5Vs Lab",
        "Periksa data, eksperimen, dan keputusan pemrosesan yang mendukung setiap V.",
    )
    name = st.radio("Karakteristik Big Data", V_NAMES, horizontal=True, key="vf_lab")
    module, concept, limits = V_DETAILS[name]
    strip(f"{name} · {module} — {concept}")
    if name == "Volume":
        volume(snapshot, repository, run_index)
    elif name == "Velocity":
        st.caption(
            "Batch asli dipublikasikan ke inbox lokal, dibaca Spark, lalu divalidasi. "
            "Kontrol di bawah menampilkan kembali urutan dan interval yang sudah tercatat."
        )
        playback(snapshot)
    elif name == "Variety":
        variety(snapshot)
    elif name == "Veracity":
        veracity(snapshot)
    elif name == "Value":
        value(snapshot)
    st.caption(f"Batas interpretasi: {limits}")


def volume(snapshot: Snapshot, repository: EvidenceRepository, run_index: list[dict]) -> None:
    data = snapshot.volume
    for col, (label, amount) in zip(
        st.columns(3),
        (
            ("Observasi sumber", snapshot.metrics.source_rows),
            ("Observasi tersimpan", snapshot.metrics.retained),
            ("Baris metadata", snapshot.run["metadata_rows"]),
        ),
        strict=True,
    ):
        col.metric(label, fmt(amount))
    a, b = st.columns([1.45, 1])
    with a, st.container(border=True, key="panel_benchmark"):
        panel_head("Benchmark Spark", "Eksperimen lokal · input sama, warm-up sebelum pengukuran")
        display = st.radio(
            "Tampilan benchmark", ("Median", "Per percobaan"), horizontal=True, key="volume_view"
        )
        fig = go.Figure()
        if display == "Median":
            fig.add_bar(
                x=list(OP_LABELS.values()),
                y=[data["median_ms"][op] for op in OP_LABELS],
                marker_color=[CYAN, TEAL],
                hovertemplate="%{x}<br>%{y:.3f} ms<extra></extra>",
            )
            fig.update_xaxes(tickangle=0)
        else:
            for op, color in zip(OP_LABELS, (CYAN, TEAL), strict=True):
                trials = sorted(
                    (r for r in data["trials"] if r["operation"] == op), key=lambda r: r["trial"]
                )
                fig.add_bar(
                    x=[r["trial"] for r in trials],
                    y=[r["elapsed_ms"] for r in trials],
                    name=OP_LABELS[op],
                    marker_color=color,
                    hovertemplate="%{y:.3f} ms",
                )
            fig.update_layout(barmode="group")
            fig.update_xaxes(title="Percobaan", dtick=1)
        fig.update_yaxes(title="Durasi (ms)", rangemode="tozero")
        plot(fig, "volume-timing", 252, legend=display != "Median")
    with b, st.container(border=True, key="panel_volume_groups"):
        panel_head("Hasil setiap operasi")
        table(
            [
                {"Operasi": name, "Grup hasil": data["output_groups"][op]}
                for op, name in OP_LABELS.items()
            ],
            key="volume_groups",
        )
        st.markdown(
            f"**A** menghitung per recording. **B** menambahkan join metadata dan mengelompokkan "
            f"baris per recording, lokasi, dan {data['window_seconds']} detik. "
            "Keduanya menghitung input yang sama; jumlah grup menjelaskan perbedaan bentuk hasil."
        )
        st.caption(
            f"Spark {data['spark_version']} · {data['master']} · "
            f"{data['shuffle_partitions']} partisi shuffle dikonfigurasi."
        )
    panel_head(
        "Skala per mode", "Angka berasal dari run yang tersedia, tanpa menyalin nilai antarmode."
    )
    table(run_index, key="volume_scale")
    with st.expander("Skema CSV dan Spark physical plan"):
        st.text(", ".join(repr(x) for x in snapshot.profiles[0]["header"]))
        table(
            [
                {"Kolom": name, "Tipe setelah integrasi": kind}
                for name, kind in snapshot.integration["integrated_spark_types"]
            ],
            key="volume_schema",
        )
        st.markdown(
            "**Scan** membaca sumber atau cache. **Aggregation** meringkas baris per kunci. "
            "**Join** menambahkan metadata. **Exchange** memindahkan atau mendistribusikan data "
            "untuk tahap berikutnya; broadcast menyebarkan sisi lookup yang kecil."
        )
        op = st.selectbox(
            "Pilih physical plan", list(OP_LABELS), format_func=OP_LABELS.get, key="volume_plan"
        )
        try:
            plan = (repository.path(snapshot.mode) / PLANS[op]).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            st.info(f"Physical plan tidak tersedia: `{PLANS[op]}`.")
        else:
            plan = re.sub(r"file:[^\],\n]+", "file:<jalur lokal disembunyikan>", plan)
            plan = re.sub(r"\b/(?:Users|home|private|var|tmp)/[^\],\n ]+", "<jalur lokal>", plan)
            st.code(plan, language="text", height=300)


def variety(snapshot: Snapshot) -> None:
    report = snapshot.integration
    with st.container(border=True, key="panel_variety_flow"):
        panel_head("Dua representasi, satu recording_id")
        st.html("""
        <div class="vf-join" aria-label="Numerics CSV dan metadata Fix menjadi hasil join Spark">
          <div><b>Numerics.csv</b><small>Observasi per detik</small></div>
          <div><b>Fix.txt → JSON Lines</b><small>Satu metadata per recording</small></div>
          <span aria-hidden="true">→</span>
          <div><b>Spark broadcast join</b><small>recording_id → Parquet</small></div>
        </div>
        """)
        st.caption(
            "Nama file dan marker Fix harus cocok. Lokasi, frekuensi, dan daftar kanal berasal dari Fix.txt."
        )
    a, b, c = st.columns(3)
    a.metric("Observasi sebelum join", fmt(report["observations_before_join"]))
    b.metric("Observasi setelah join", fmt(report["observations_after_join"]))
    c.metric("Recording cocok", fmt(report["metadata_rows"]))
    panel_head(
        "Kardinalitas: banyak ke satu",
        "Banyak observasi numerik terhubung ke tepat satu baris JSON.",
    )
    labels = {
        "source_ids_without_metadata": "CSV tanpa metadata",
        "metadata_ids_without_source": "Metadata tanpa CSV",
        "duplicate_metadata_ids": "Kunci metadata duplikat",
        "missing_source_ids": "Kunci sumber hilang",
        "unexpected_source_ids": "Kunci sumber tidak diharapkan",
    }
    table(
        [{"Pemeriksaan": labels[key], "Jumlah": len(report[key])} for key in KEY_CHECKS],
        key="variety_keys",
    )
    with st.expander("Bandingkan skema sumber", expanded=True):
        left, right = st.columns(2)
        with left:
            panel_head("CSV · observasi")
            table(
                [{"Kolom": k, "Tipe Spark": v} for k, v in report["csv_spark_types"]],
                key="csv_schema",
            )
        with right:
            panel_head("JSON · metadata")
            table(
                [{"Kolom": k, "Tipe Spark": v} for k, v in report["json_spark_types"]],
                key="json_schema",
            )
    with st.expander("Metadata JSON dan contoh hasil join"):
        rid = st.selectbox("Recording metadata", snapshot.ids, key="variety_rid")
        st.json(snapshot.metadata[rid], expanded=True)
        st.caption("Contoh di bawah adalah sampel resmi yang disimpan pada integration.json.")
        table(
            pd.DataFrame(report["sample_joined_observations"])[
                ["recording_id", "time_s", *MEASURES, "location", "numerics_sampling_hz"]
            ],
            key="join_example",
        )


def veracity(snapshot: Snapshot) -> None:
    scenario = st.radio(
        "Skenario bukti",
        ("source", "fixture"),
        format_func={
            "source": "Sumber PhysioNet",
            "fixture": "Fixture sintetis",
        }.get,
        horizontal=True,
        key="quality_scenario",
    )
    report = snapshot.report(scenario)
    before, after, actions = (report[k] for k in ("before", "after", "actions"))
    if scenario == "source":
        st.caption("Audit dari Numerics.csv resmi · nilai kosong dihitung sebelum validasi.")
        for col, (label, amount) in zip(
            st.columns(4),
            (
                ("Sel hilang di sumber", sum(before["source_missing_by_measure"].values())),
                ("Timestamp negatif", before["field_status_counts"]["time_s"]["out_of_range"]),
                ("Baris berlebih (kunci sama)", before["repeated_valid_keys"]["excess_rows"]),
                ("Duplikat persis", before["exact_duplicate_source_rows_beyond_first"]),
            ),
            strict=True,
        ):
            col.metric(label, fmt(amount))
        invalid = report["invalid_time_rows_by_recording"]
        if invalid:
            st.warning(
                "Timestamp invalid dikeluarkan di: "
                + ", ".join(f"{r['recording_id']} ({r['invalid_time_rows']})" for r in invalid)
                + "."
            )
        a, b = st.columns([1, 1.45])
        with a, st.container(border=True, key="panel_source_missing"):
            panel_head("Sel hilang menurut kanal", "NaN dan sel kosong pada sumber")
            plot(missing_bars(before["source_missing_by_measure"]), "veracity_missing", 250)
        with b, st.container(border=True, key="panel_recording_coverage"):
            panel_head("Kelengkapan per recording", "Persentase sel terisi setelah validasi")
            cleaned = clean_missing_by_recording(snapshot)
            sorted_rows = cleaned.sort_values(["complete_pct", "recording_id"])
            fig = go.Figure(
                go.Bar(
                    x=sorted_rows["recording_id"].tolist(),
                    y=sorted_rows["complete_pct"].tolist(),
                    customdata=sorted_rows["missing"].tolist(),
                    marker_color=TEAL,
                    hovertemplate="%{x}<br>%{y:.2f}% lengkap<br>%{customdata} sel hilang<extra></extra>",
                )
            )
            fig.update_xaxes(type="category", nticks=9, tickangle=-35)
            fig.update_yaxes(title="Kelengkapan (%)", range=[0, 105])
            plot(fig, "veracity_completeness", 250)
        with st.expander("Nilai hilang per recording · sebelum validasi"):
            channel = st.selectbox(
                "Kanal audit sumber",
                MEASURES,
                format_func=lambda c: CHANNELS[c].label,
                key="quality_channel",
            )
            table(
                source_missing_by_recording(snapshot, channel)
                .sort_values(["missing", "recording_id"], ascending=[False, True])
                .rename(
                    columns={
                        "recording_id": "Recording ID",
                        "missing": "Sel hilang",
                        "rows": "Baris sumber",
                    }
                ),
                key="source_missing_recording",
                height=250,
            )
        with st.expander("Cakupan waktu · setelah validasi"):
            table(snapshot.coverage, key="time_coverage", height=240)
    else:
        st.warning(
            "Fixture ini sengaja dibuat untuk menguji aturan. Barisnya tidak berasal dari PhysioNet "
            "dan tidak masuk ke Parquet, benchmark, atau analitik fisiologis."
        )
        a, b, c = st.columns(3)
        a.metric("Baris fixture", fmt(before["rows"]))
        b.metric("Timestamp invalid dibuang", fmt(actions["invalid_time_rows_dropped"]))
        c.metric("Duplikat kunci dibuang", fmt(actions["duplicate_key_rows_dropped"]))
        panel_head("Uji aturan validasi")
        issues = ("malformed", "nonfinite", "out_of_range", "blank", "nan")
        breakdown = before["field_status_counts"]
        fig = go.Figure()
        for key, name in zip(
            issues, ("Format salah", "Tidak hingga", "Di luar batas", "Kosong", "NaN"), strict=True
        ):
            fig.add_bar(
                x=["Waktu", *(CHANNELS[c].label for c in MEASURES)],
                y=[breakdown[c][key] for c in ("time_s", *MEASURES)],
                name=name,
            )
        fig.update_layout(barmode="stack")
        fig.update_yaxes(title="Jumlah sel", dtick=1)
        plot(fig, "fixture_issues", 245, legend=True)
    panel_head(
        "Sebelum dan sesudah",
        "Kelengkapan bukan alasan untuk mengganti bacaan dengan angka perkiraan.",
    )
    table(
        [
            {"Pemeriksaan": name, "Sebelum": a, "Sesudah": b}
            for name, a, b in (
                ("Baris", before["rows"], after["rows"]),
                ("Timestamp invalid", before["invalid_time_rows"], after["invalid_time_rows"]),
                (
                    "Baris berlebih karena kunci sama",
                    before["repeated_valid_keys"]["excess_rows"],
                    after["duplicate_key_rows"],
                ),
                (
                    "Baris dengan kanal kosong atau invalid",
                    before["incomplete_rows"],
                    after["incomplete_rows"],
                ),
            )
        ],
        key="veracity_before_after",
    )
    st.caption(
        "Waktu harus finite dan ≥ 0. Pengukuran tak terbaca atau di luar batas format menjadi null. "
        "Untuk kunci duplikat, dipilih baris dengan kanal valid terbanyak, lalu diurutkan secara deterministik."
    )


def value(snapshot: Snapshot) -> None:
    with st.container(border=True, key="panel_value_filters"):
        a, b = st.columns(2)
        channel = a.selectbox(
            "Kanal analitik", MEASURES, format_func=lambda c: CHANNELS[c].label, key="value_channel"
        )
        rid = b.selectbox("Recording untuk tren", snapshot.ids, key=f"value_rid_{snapshot.mode}")
    info = CHANNELS[channel]
    a, b = st.columns(2)
    with a, st.container(border=True, key="panel_value_recordings"):
        panel_head(f"Rata-rata {info.label} per recording", "Spark SQL · hanya pengukuran valid")
        plot(recording_bars(snapshot.recordings, channel), "value_recordings", 271)
    with b, st.container(border=True, key="panel_value_trend"):
        panel_head(
            f"{info.label} sepanjang {rid}",
            f"Rata-rata per {snapshot.run['analytics_window_seconds']} detik",
        )
        windows = snapshot.windows[snapshot.windows["recording_id"] == rid]
        plot(
            window_trend(windows, channel, snapshot.run["analytics_window_seconds"]),
            "value_trend",
            271,
        )
    observed = snapshot.recordings.set_index("recording_id").loc[rid]
    table(
        [
            {
                "Kanal": CHANNELS[c].label,
                "Unit": CHANNELS[c].unit,
                "Rata-rata": observed[f"{c}_mean"],
                "Valid": int(observed[f"{c}_valid"]),
                "Total": int(observed["rows"]),
                "Kelengkapan (%)": 100 * observed[f"{c}_valid"] / observed["rows"],
            }
            for c in MEASURES
        ],
        key="value_reading_counts",
        columns={
            "Rata-rata": st.column_config.NumberColumn(format="%.2f"),
            "Kelengkapan (%)": st.column_config.NumberColumn(format="%.1f"),
        },
    )
    panel_head("Insight yang dapat ditelusuri")
    weakest = snapshot.recordings.sort_values(["resp_completeness", "recording_id"]).iloc[0]
    missing = int(weakest["rows"] - weakest["resp_valid"])
    if missing:
        strip(
            f"RESP dengan kelengkapan terendah: {weakest['recording_id']} memiliki "
            f"{fmt(weakest['resp_valid'])}/{fmt(weakest['rows'])} bacaan valid "
            f"({fmt(100 * weakest['resp_valid'] / weakest['rows'], 1)}%). Periksa ketersediaan sebelum membaca rata-rata."
        )
    else:
        strip("Pada mode ini, seluruh rekaman memiliki RESP lengkap pada baris yang dipertahankan.")
    if (pair := complete_minute_pair(snapshot, snapshot.ids[0])) is not None:
        first, last = pair
        with st.expander(
            f"{snapshot.ids[0]} · bandingkan jendela lengkap pertama dan terakhir", expanded=True
        ):
            width = snapshot.run["analytics_window_seconds"]
            first_start, last_start = int(first["window_start_s"]), int(last["window_start_s"])
            st.caption(
                f"Jendela [{first_start}, {first_start + width}) dan [{last_start}, {last_start + width}) detik, "
                f"masing-masing {fmt(first['rows'])} bacaan valid untuk keempat kanal."
            )
            table(
                [
                    {
                        "Kanal": CHANNELS[c].label,
                        "Unit": CHANNELS[c].unit,
                        "Rata-rata pertama": first[f"{c}_mean"],
                        "Rata-rata terakhir": last[f"{c}_mean"],
                    }
                    for c in MEASURES
                ],
                key="value_compare",
                columns={
                    k: st.column_config.NumberColumn(format="%.2f")
                    for k in ("Rata-rata pertama", "Rata-rata terakhir")
                },
            )
    st.caption(
        f"Sumber: {RECORDINGS} dan {WINDOWS}. Skala tren menyesuaikan kanal. Arahkan kursor untuk melihat penyebut setiap titik. "
        "Jendela terakhir dapat memuat satu pengukuran saja."
    )
