"""Architecture and academic evidence pages."""

from base64 import b64encode
from dataclasses import dataclass
from html import escape
from xml.etree import ElementTree

import pandas as pd
import streamlit as st

from .design import (
    AMBER,
    BG,
    BORDER,
    CYAN,
    MUTED,
    SURFACE,
    TEAL,
    TEXT,
    fmt,
    page_head,
    panel_head,
    table,
)
from .evidence import (
    COVERAGE,
    FIXTURE,
    INTEGRATION,
    METADATA,
    PARQUET,
    PROVENANCE,
    QUALITY,
    RECORDINGS,
    RUN,
    SCHEMA,
    VELOCITY,
    VOLUME,
    WINDOWS,
    EvidenceRepository,
    Snapshot,
    stamp,
)
from .overview import WIB


@dataclass(frozen=True)
class Stage:
    title: str
    category: str
    short: str
    technology: str
    input: str
    output: str
    characteristic: str


STAGES = (
    Stage(
        "File resmi PhysioNet",
        "Sumber",
        "Numerics.csv + Fix.txt",
        "PhysioNet BIDMC",
        "Rekaman monitor rumah sakit historis",
        "Berkas numerik dan metadata tetap",
        "Volume · Variety",
    ),
    Stage(
        "Cache lokal terverifikasi",
        "Ingestion",
        "SHA-256 + pemeriksaan bentuk",
        "Python + checksum resmi",
        "Respons unduhan dan manifest SHA-256",
        "Berkas asli yang dipertahankan apa adanya",
        "Veracity",
    ),
    Stage(
        "Historical batch replay",
        "Eksperimen",
        "Inbox lokal dan waktu tiba",
        "Python scheduler + PySpark",
        "Salinan data historis per jendela waktu rekaman",
        "Log batch, waktu tiba, antre, dan proses",
        "Velocity",
    ),
    Stage(
        "Parsing dan validasi",
        "Transformasi",
        "Tipe numerik, null, kunci",
        "PySpark DataFrame",
        "CSV numerik dari cache",
        "Observasi bertipe dengan waktu valid dan kunci unik",
        "Veracity",
    ),
    Stage(
        "Integrasi CSV / JSON",
        "Pemrosesan",
        "Join dengan recording_id",
        "Spark broadcast join",
        "Observasi bersih dan metadata JSON dari Fix.txt",
        "Observasi dengan metadata terverifikasi",
        "Variety · Volume",
    ),
    Stage(
        "Penyimpanan Parquet",
        "Penyimpanan",
        "Kolumnar + baca balik",
        "Apache Parquet",
        "Data yang sudah diintegrasikan",
        "Berkas kolumnar dan jumlah baris yang direkonsiliasi",
        "Volume · Veracity",
    ),
    Stage(
        "Analitik Spark SQL",
        "Analitik",
        "Ringkasan rekaman dan waktu",
        "Spark SQL",
        "Data Parquet yang dibaca balik",
        "Rata-rata, minimum, maksimum, dan kelengkapan",
        "Value",
    ),
    Stage(
        "Dashboard dan bukti",
        "Keluaran",
        "Data, audit, dan eksperimen",
        "Streamlit + Plotly + PyArrow",
        "Artefak ringkas, log replay, dan Parquet untuk satu recording",
        "Visualisasi lokal tanpa memulai Spark",
        "Semua 5Vs",
    ),
)
STAGE_POSITIONS = (
    (20, 57),
    (278, 57),
    (20, 207),
    (536, 57),
    (794, 57),
    (794, 207),
    (536, 207),
    (278, 207),
)
TEST_REPORT = "dashboard-qa/pytest.xml"
DOWNLOADS = (
    RUN,
    PROVENANCE,
    SCHEMA,
    INTEGRATION,
    METADATA,
    QUALITY,
    FIXTURE,
    COVERAGE,
    RECORDINGS,
    WINDOWS,
    VOLUME,
    VELOCITY,
    "benchmarks/velocity_batches.csv",
)


def architecture_svg() -> str:
    nodes = []
    for i, (stage, (x, y)) in enumerate(zip(STAGES, STAGE_POSITIONS, strict=True)):
        color = AMBER if i == 2 else TEAL if i == 7 else CYAN
        nodes.append(f"""
          <g transform="translate({x} {y})">
            <rect width="225" height="90" rx="10" fill="{SURFACE}" stroke="{BORDER}"/>
            <text x="15" y="24" fill="{color}" font-size="11" font-weight="700" letter-spacing="1.2">
              {i + 1:02d} · {escape(stage.category.upper())}
            </text>
            <text x="15" y="50" fill="{TEXT}" font-size="15.5" font-weight="700">{escape(stage.title)}</text>
            <text x="15" y="72" fill="{MUTED}" font-size="12.5">{escape(stage.short)}</text>
          </g>""")
    arrows = [
        "M247 102 H271",
        "M505 102 H529",
        "M763 102 H787",
        "M907 150 V201",
        "M791 251 H767",
        "M533 251 H509",
    ]
    lines = "".join(
        f'<path d="{d}" fill="none" stroke="{CYAN}" stroke-width="1.6" marker-end="url(#vf-arrow)"/>'
        for d in arrows
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1040 318" role="img"
     aria-labelledby="vf-flow-title" font-family="system-ui, sans-serif">
     <title id="vf-flow-title">Arsitektur VitalFlow, alur batch utama dan cabang eksperimen replay</title>
     <defs><marker id="vf-arrow" viewBox="0 0 8 8" markerWidth="6" markerHeight="6"
       refX="7" refY="4" orient="auto-start-reverse"><path d="M0 0 L8 4 L0 8 Z" fill="{CYAN}"/></marker></defs>
     <rect width="1040" height="318" rx="12" fill="{BG}"/>
     <text x="20" y="33" fill="{TEXT}" font-size="13" letter-spacing="1.2" font-weight="700">ALUR BATCH UTAMA</text>
     <text x="1018" y="33" text-anchor="end" fill="{MUTED}" font-size="12">Berkas lokal · Apache Spark</text>
     {lines}
     <path d="M390 151 V177 H132 V201" fill="none" stroke="{AMBER}" stroke-width="1.7" stroke-dasharray="5 5"/>
     <path d="M128 195 L132 201 L136 195" fill="none" stroke="{AMBER}" stroke-width="1.7"/>
     <text x="151" y="169" fill="{AMBER}" font-size="11.5">Cabang replay · memakai validasi yang sama</text>
     {"".join(nodes)}
     </svg>'''


def architecture() -> None:
    page_head(
        "04 / ALUR SISTEM",
        "System Architecture",
        "Ikuti satu alur dari berkas PhysioNet hingga hasil SQL dan bukti yang dapat diperiksa.",
    )
    svg = architecture_svg()
    with st.container(border=True, key="panel_architecture"):
        panel_head(
            "Alur data VitalFlow",
            "Garis putus-putus: eksperimen replay berjalan sebagai cabang dari cache.",
        )
        nodes = "".join(
            f"<li>{escape(stage.title)} · {escape(stage.short)}</li>" for stage in STAGES
        )
        encoded = b64encode(svg.encode("utf-8")).decode("ascii")
        st.html(
            f'<div class="vf-flow"><img width="1040" height="318" '
            'alt="File PhysioNet → cache → validasi → integrasi → Parquet → SQL → dashboard. '
            'Replay berjalan pada cabang terpisah dari cache." '
            f'src="data:image/svg+xml;base64,{encoded}">'
            f'<ol class="vf-flow-mobile">{nodes}</ol></div>'
        )
        st.download_button(
            "Unduh diagram SVG",
            data=svg,
            file_name="vitalflow-architecture.svg",
            mime="image/svg+xml",
            key="architecture_svg",
            on_click="ignore",
        )
    names = [stage.title for stage in STAGES]
    chosen = st.selectbox("Telusuri komponen", names, key="architecture_stage")
    stage = STAGES[names.index(chosen)]
    with st.container(border=True, key="panel_stage"):
        panel_head(stage.title, f"{stage.category} · {stage.characteristic}")
        table(
            [
                {"Aspek": label, "Rincian": description}
                for label, description in (
                    ("Teknologi", stage.technology),
                    ("Input", stage.input),
                    ("Output", stage.output),
                )
            ],
            key="architecture_details",
        )
    st.caption(
        "Eksperimen replay membaca batch yang tiba dan menjalankan ekspresi validasi yang sama. "
        "Hasil benchmark menjadi bukti terpisah; tabel analitik dibuat dari jalur batch utama."
    )


def test_summary(repository: EvidenceRepository) -> str | None:
    path = repository.project.outputs / TEST_REPORT
    try:
        root = ElementTree.parse(path).getroot()
        suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
        counts = {
            name: sum(int(s.attrib.get(name, "0")) for s in suites)
            for name in ("tests", "failures", "errors", "skipped")
        }
        if not suites or counts["tests"] <= 0 or any(value < 0 for value in counts.values()):
            return None
        passed = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
        if passed < 0:
            return None
    except (OSError, ValueError, ElementTree.ParseError):
        return None
    return (
        f"{passed} lulus · {counts['failures']} gagal · {counts['errors']} error · "
        f"{counts['skipped']} dilewati. Sumber: outputs/{TEST_REPORT}."
    )


def evidence(snapshot: Snapshot, repository: EvidenceRepository) -> None:
    page_head(
        "05 / VERIFIKASI AKADEMIK",
        "Evidence & Methodology",
        "Telusuri asal data, periksa bukti rubrik, dan lihat batasan analisis.",
    )
    provenance, run = snapshot.provenance, snapshot.run
    files = provenance["files"]
    meta = run["runtime"]
    finished = stamp(run["completed_at_utc"]).astimezone(WIB).strftime("%d/%m/%Y · %H:%M:%S WIB")
    a, b = st.columns(2)
    with a, st.container(border=True, key="panel_provenance"):
        panel_head("Sumber terverifikasi", provenance["dataset"])
        st.markdown(f"**Versi {provenance['version']}** · DOI {provenance['doi']}")
        st.markdown(
            f"[Halaman dataset resmi]({provenance['dataset_page']}) · {provenance['license']}"
        )
        st.write(
            f"{fmt(len(files))} file sumber dicatat dengan SHA-256 · "
            f"{fmt(sum(f['bytes'] for f in files))} byte."
        )
        st.caption(
            f"Run ini membaca {fmt(sum(f['status'] == 'cached' for f in files))} file dari cache. "
            "Status berasal dari manifest pipeline."
        )
    with b, st.container(border=True, key="panel_environment"):
        panel_head("Run dan lingkungan", f"{snapshot.mode.title()} · {snapshot.folder}")
        st.write(f"**Spark {meta['spark']}** · {meta['spark_master']}")
        st.write(f"Python {meta['python']} · Java {meta['java']} · {meta['os']} {meta['machine']}")
        st.caption(f"Selesai {finished} · {fmt(run['elapsed_seconds'], 2)} detik")
        if result := test_summary(repository):
            st.caption(f"QA terakhir yang tercatat: {result}")
        else:
            st.caption("Laporan pengujian dashboard belum tersedia pada checkout ini.")
    panel_head("Cakupan rubrik")
    parquet_found = any((repository.path(snapshot.mode) / PARQUET).glob("*.parquet"))
    rubric = [
        ("Volume", "Group/count dan join per jendela", VOLUME, "Durasi lokal"),
        ("Velocity", "Batch, interval, antre, proses", VELOCITY, "Replay historis"),
        ("Variety", "CSV + Fix → JSON, kunci recording_id", INTEGRATION, "Satu dataset"),
        (
            "Veracity",
            "Audit asli dan uji sintetis terpisah",
            f"{QUALITY} · {FIXTURE}",
            "Aturan format",
        ),
        ("Value", "Tren, rata-rata, jumlah valid", f"{RECORDINGS} · {WINDOWS}", "Observasional"),
        ("Penyimpanan", "Parquet dan rekonsiliasi readback", PARQUET, "Berkas lokal"),
    ]
    table(
        [
            {
                "Persyaratan": name,
                "Implementasi": implementation,
                "Berkas bukti": filename,
                "Status": "Tersedia"
                if name != "Penyimpanan" or parquet_found
                else "Parquet tidak ditemukan",
                "Batasan": limitation,
            }
            for name, implementation, filename, limitation in rubric
        ],
        key="rubric_table",
        height=248,
    )
    with st.expander("Inspeksi dan unduh artefak"):
        st.caption(f"Direktori run: {snapshot.folder}/ · hanya artefak terpilih.")
        artifact = st.selectbox("Berkas bukti", DOWNLOADS, key="evidence_download_file")
        try:
            contents = (repository.path(snapshot.mode) / artifact).read_bytes()
        except OSError:
            st.info("Berkas tidak tersedia. Muat ulang dashboard atau buat ulang run terkait.")
        else:
            st.download_button(
                "Unduh berkas",
                contents,
                file_name=artifact.rsplit("/", 1)[-1],
                mime="application/octet-stream",
                key="evidence_download",
                on_click="ignore",
            )
        table(
            pd.DataFrame(files)[["recording_id", "relative_path", "bytes", "sha256", "status"]],
            key="evidence_manifest",
            height=220,
        )
    with st.expander("Metodologi, keterbatasan, dan etika", expanded=True):
        st.markdown("""
- **Kelengkapan** = sel kanal terisi ÷ semua sel kanal pada baris yang dipertahankan. Nilai ini bukan uptime sensor.
- **Benchmark** mengukur tindakan Spark lokal pada input cache. Replay mengukur kedatangan batch lokal dan tidak menyimulasikan latensi jaringan medis.
- **Null tidak diimputasi.** Periksa jumlah bacaan valid sebelum menarik kesimpulan. Rekaman pendek dan historis tidak mewakili semua pasien.
- **Privasi.** Antarmuka hanya memakai recording ID dan field metadata yang diizinkan. Aplikasi ini untuk pendidikan, bukan diagnosis atau pemantauan klinis.
        """)
        st.caption(
            "Referensi lokal: docs/dataset.md · docs/methodology.md · docs/evidence-matrix.md"
        )
