"""Create and validate the three-page VitalFlow ETS document."""

import argparse
import io
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

import reportlab
from pypdf import PdfReader
from reportlab.graphics import renderPDF, renderSVG
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from submission_architecture import diagram

from vitalflow.config import DATASET_DOI, DATASET_PAGE, DATASET_VERSION, PROJECT_ROOT, Project
from vitalflow.dashboard.analysis import complete_minute_pair
from vitalflow.dashboard.design import fmt
from vitalflow.dashboard.evidence import EvidenceRepository, stamp

W, H = A4
M = 46
BODY = W - 2 * M
INK, TEAL, TEXT, LINE, PALE = map(HexColor, ("#132B42", "#007870", "#405970", "#D5E0E8", "#ECF7F5"))
DRAFT = "DRAF - BELUM UNTUK DIKUMPULKAN"
EMPTY = "Belum diisi"
LABELS = (
    "Project Lead / Analyst",
    "System Engineer",
    "Data Engineer",
    "Big Data Developer",
    "Data Analyst",
)
SUB = PROJECT_ROOT / "docs/submission"


def youtube_link(value):
    if not value:
        return ""
    parts = urlsplit(value)
    if parts.scheme != "https" or parts.netloc not in {
        "youtu.be",
        "www.youtube.com",
        "youtube.com",
    }:
        raise ValueError("URL video harus menggunakan HTTPS dan domain YouTube.")
    if parts.netloc == "youtu.be":
        video = parts.path.removeprefix("/")
    elif parts.path == "/watch":
        video = parse_qs(parts.query).get("v", [""])[0]
    else:
        video = ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video):
        raise ValueError("Gunakan tautan video YouTube /watch?v=... atau youtu.be/....")
    return f"https://www.youtube.com/watch?v={video}"


def details(path, draft):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Berkas identitas harus berupa objek JSON.")

    def get(obj, key):
        value = obj.get(key, "")
        if not isinstance(value, str):
            raise ValueError(f"{key} harus berupa teks JSON, termasuk NIM dan nomor kelompok.")
        return " ".join(value.split())

    group = get(data, "group_number")
    if group and not re.fullmatch(r"[0-9]{1,8}", group):
        raise ValueError("Nomor kelompok harus berisi angka.")
    students = data.get("students")
    if not isinstance(students, list) or len(students) != 5:
        raise ValueError("Masukkan tepat lima anggota.")
    team = []
    for item in students:
        if not isinstance(item, dict):
            raise ValueError("Setiap anggota harus memiliki field name dan nim.")
        name, nim = get(item, "name"), get(item, "nim")
        if name and (
            len(name) > 85
            or not any(c.isalpha() for c in name)
            or not all(c.isalpha() or c in " .-'’" for c in name)
            or re.search(
                r"\b(?:placeholder|contoh|nama anggota|nama lengkap|dummy|belum diisi)\b",
                name,
                re.IGNORECASE,
            )
        ):
            raise ValueError("Isi nama asli (huruf, spasi, titik, tanda hubung atau apostrof).")
        if nim and not re.fullmatch(r"[0-9]{3,24}", nim):
            raise ValueError("NIM harus berisi angka.")
        team.append((name, nim))
    nims = [nim for _, nim in team if nim]
    if len(nims) != len(set(nims)):
        raise ValueError("NIM harus unik.")
    url = youtube_link(get(data, "youtube_url"))
    if not draft and not (group and url and all(name and nim for name, nim in team)):
        raise ValueError("Mode final memerlukan nomor kelompok, lima nama/NIM, dan URL video.")
    return group, team, url


class Report:
    def __init__(self, draft):
        for name, filename in (("VF", "Vera.ttf"), ("VF-Bold", "VeraBd.ttf")):
            font = Path(reportlab.__file__).parent / "fonts" / filename
            pdfmetrics.registerFont(TTFont(name, str(font)))
        self.buffer = io.BytesIO()
        self.c = canvas.Canvas(self.buffer, pagesize=A4, invariant=1)
        self.c.setTitle(f"VitalFlow | ETS IFB-451{' | DRAF' if draft else ''}")
        self.c.setAuthor("VitalFlow")
        self.draft = draft

    def rect(self, x, y, w, h, color):
        self.c.setFillColor(color)
        self.c.rect(x, H - y - h, w, h, fill=1, stroke=0)

    def text(self, value, y, *, x=M, w=BODY, size=10, bold=False, color=INK, max_h=72):
        style = ParagraphStyle(
            "vf",
            fontName="VF-Bold" if bold else "VF",
            fontSize=size,
            leading=size * 1.37,
            textColor=color,
            alignment=TA_LEFT,
        )
        paragraph = Paragraph(escape(str(value)), style)
        _, height = paragraph.wrap(w, H)
        if height > max_h or x < M or x + w > W - M + 0.01 or y < 0 or y + height > H - 28:
            raise ValueError(f"Teks tidak muat dalam tata letak: {value!r}")
        paragraph.drawOn(self.c, x, H - y - height)
        return height

    def link(self, url, y, *, x=M, w=BODY, size=9):
        height = self.text(url, y, x=x, w=w, size=size, color=TEAL, max_h=26)
        self.c.linkURL(url, (x, H - y - height, x + w, H - y), relative=0)

    def header(self, page, title, subtitle):
        self.rect(0, 0, W, 6, TEAL)
        self.text("VITALFLOW  /  ETS IFB-451 BIG DATA", 35, color=TEAL, bold=True, size=9)
        self.text(title, 64, bold=True, size=29, max_h=44)
        self.text(subtitle, 111, color=TEXT, size=10, max_h=31)
        self.rect(M, 143, BODY, 0.8, LINE)
        self.rect(M, 783, BODY, 0.8, LINE)
        self.text("ITENAS BANDUNG  /  INFORMATIKA  /  2026-2027", 798, size=7.7, color=TEXT)
        self.text(f"0{page} / 03", 798, x=W - M - 48, w=48, size=8, color=TEAL, bold=True)
        if self.draft:
            self.text(DRAFT, 764, color=TEAL, size=8.5, bold=True)

    def page_one(self, snapshot, group, team):
        self.header(1, "Informasi proyek", "Studi kasus 07  /  IoT-Based Patient Monitoring")
        self.text("VitalFlow", 169, size=34, bold=True, max_h=50)
        self.text(
            "IoT Patient Monitoring & Big Data Analytics", 221, size=15, bold=True, color=TEAL
        )
        self.text(
            "Institut Teknologi Nasional (Itenas) Bandung | Program Studi Informatika",
            249,
            size=9.5,
            color=TEXT,
        )
        self.text("Pertanyaan pemantauan", 287, bold=True, size=13)
        self.text(
            "Bagaimana nilai dan ketersediaan HR, nadi, laju napas, dan saturasi oksigen "
            "berubah selama satu rekaman? VitalFlow menggunakan ringkasan per rekaman dan "
            "per menit untuk membantu meninjau tren bersama jumlah bacaan valid.",
            312,
        )
        self.rect(M, 374, BODY, 127, PALE)
        self.text(
            "SUMBER DATA  /  PHYSIONET", 387, x=M + 13, w=BODY - 26, size=8.5, color=TEAL, bold=True
        )
        self.text(
            f"BIDMC PPG and Respiration Dataset v{DATASET_VERSION}",
            404,
            x=M + 13,
            w=BODY - 26,
            size=11,
            bold=True,
        )
        self.text(
            f"{fmt(snapshot.metrics.recordings)} rekaman historis sekitar delapan menit; "
            "nilai numerik 1 Hz dari Numerics.csv dan metadata terpilih dari Fix.txt. "
            "Sinyal gelombang tidak dianalisis.",
            426,
            x=M + 13,
            w=BODY - 26,
            size=9.5,
        )
        self.link(DATASET_PAGE, 459, x=M + 13, w=BODY - 26)
        self.text(
            f"Pimentel, Johnson, Charlton & Clifton (2018) | DOI {DATASET_DOI}",
            478,
            x=M + 13,
            w=BODY - 26,
            size=8.4,
            color=TEXT,
        )
        self.text(f"Kelompok: {group or EMPTY}", 520, bold=True, size=13)
        self.rect(M, 547, BODY, 24, INK)
        for label, x, w in (
            ("Nama anggota", M + 11, 260),
            ("NIM", M + 266, 111),
            ("Peran", M + 382, BODY - 390),
        ):
            self.text(label, 554, x=x, w=w, size=8.4, bold=True, color=white)
        for i, ((name, nim), role) in enumerate(zip(team, LABELS, strict=True)):
            y = 571 + 34 * i
            if i % 2 == 0:
                self.rect(M, y, BODY, 34, HexColor("#F2F6F8"))
            self.text(
                name or f"{EMPTY} (anggota {i + 1})", y + 5, x=M + 11, w=247, size=9, max_h=25
            )
            self.text(nim or EMPTY, y + 5, x=M + 266, w=111, size=8.5, max_h=24)
            self.text(role, y + 5, x=M + 382, w=BODY - 390, size=8, max_h=23)
        self.c.showPage()

    def page_two(self, s, url):
        self.header(
            2, "Video dan bukti 5Vs", "Complete mode  /  Data historis dan eksperimen lokal"
        )
        self.text("Video demonstrasi kelompok", 162, bold=True, size=13)
        if url:
            self.link(url, 187)
        else:
            self.text(f"{EMPTY} - URL YouTube menunggu video kelompok.", 187, color=TEXT)
        m = s.metrics
        v = s.volume
        batches = s.velocity["batches"]
        gaps = [b["arrival_interval_ms"] for b in batches if b["arrival_interval_ms"] is not None]
        throughput = sum(b["processed_rows"] for b in batches) / (
            sum(b["spark_ingest_and_process_ms"] for b in batches) / 1000
        )
        worst = s.recordings.loc[(s.recordings["resp_valid"] / s.recordings["rows"]).idxmin()]
        pair = complete_minute_pair(s, s.ids[0])
        if pair is None:
            raise ValueError("Bukti tidak memuat pasangan menit lengkap pada rekaman pertama.")
        first, last = pair
        quality = s.quality["before"]
        evidence = (
            (
                "01  VOLUME",
                f"{fmt(m.source_rows)} baris sumber; {fmt(m.retained)} tersimpan. "
                f"Hitung per rekaman: {fmt(v['output_groups']['aggregation'])} grup, median "
                f"{fmt(v['median_ms']['aggregation'], 1)} ms. Join dan jendela {v['window_seconds']} detik: "
                f"{fmt(v['output_groups']['join_and_window'])} grup, median "
                f"{fmt(v['median_ms']['join_and_window'], 1)} ms. Input observasi sama.",
            ),
            (
                "02  VELOCITY",
                f"{len(batches)} batch historis; target {fmt(s.velocity['target_arrival_interval_s'], 1)} detik. "
                f"Jeda terukur {fmt(min(gaps), 1)}–{fmt(max(gaps), 1)} ms; median tiba hingga selesai "
                f"{fmt(m.median_arrival_ms, 1)} ms. Laju saat Spark aktif: sekitar "
                f"{fmt(throughput)} baris/detik (baris dibagi total waktu ingest dan proses).",
            ),
            (
                "03  VARIETY",
                f"Numerics.csv bergabung dengan {fmt(s.integration['metadata_rows'])} "
                "metadata JSON Lines turunan Fix.txt. Join banyak-ke-satu dengan recording_id; "
                f"{fmt(s.run['joined_rows'])} observasi terjaga sebelum dan sesudah join.",
            ),
            (
                "04  VERACITY",
                f"Sumber: {fmt(sum(quality['source_missing_by_measure'].values()))} sel hilang, "
                f"{fmt(s.run['invalid_time_rows_dropped'])} timestamp negatif dikeluarkan, "
                f"{fmt(s.run['duplicate_key_rows_dropped'])} baris dengan kunci duplikat dibuang. "
                f"Kelengkapan sel tersimpan {fmt(m.completeness * 100, 2)}%; nilai hilang tetap null. "
                "Uji sintetis diaudit terpisah.",
            ),
            (
                "05  VALUE",
                f"Spark SQL: RESP {worst['recording_id']} memiliki "
                f"{fmt(worst['resp_valid'])} dari {fmt(worst['rows'])} bacaan valid. Pada {s.ids[0]}, "
                f"rata-rata HR menit lengkap pertama {fmt(first['hr_mean'], 2)} dan terakhir "
                f"{fmt(last['hr_mean'], 2)} denyut/menit. Periksa cakupan sebelum menafsirkan perubahan.",
            ),
        )
        for i, (label, value) in enumerate(evidence):
            y = 229 + i * 86
            self.rect(M, y, BODY, 74, PALE if i % 2 == 0 else HexColor("#F2F6F8"))
            self.text(label, y + 9, x=M + 11, w=BODY - 22, bold=True, size=8.3, color=TEAL)
            self.text(value, y + 25, x=M + 11, w=BODY - 22, size=9.4, max_h=42)
        self.text("Batas interpretasi", 664, size=11, bold=True)
        self.text(
            "Rekaman historis pendek dan observasional. Hasil membantu meninjau kualitas "
            "data monitor; tidak menjelaskan penyebab perubahan, menentukan diagnosis, "
            "atau mengukur latensi alat. Timing Spark lokal tidak membuktikan skalabilitas.",
            684,
            size=9.3,
            color=TEXT,
        )
        at = stamp(s.run["completed_at_utc"]).astimezone(ZoneInfo("Asia/Jakarta"))
        self.text(
            f"Bukti: {s.folder}/  |  Snapshot {at:%d-%m-%Y %H:%M:%S} WIB", 739, size=8.2, color=TEXT
        )
        self.c.showPage()

    def page_three(self):
        self.header(3, "Arsitektur sistem", "Alur pengolahan lokal dan cabang eksperimen")
        self.text(
            "Garis utuh: jalur data utama. Garis putus: replay, uji, dan aliran bukti.",
            160,
            color=TEXT,
            size=9,
        )
        renderPDF.draw(diagram(), self.c, M, H - 183 - 476)
        self.rect(M, 683, BODY, 65, PALE)
        self.text(
            "Satu lingkungan lokal", 693, x=M + 12, w=BODY - 24, bold=True, size=9, color=TEAL
        )
        self.text(
            "PySpark memproses data dan menulis bukti. Dashboard membuka hasil tersimpan "
            "secara lokal. Replay mengukur batch historis secara terpisah dari jalur Parquet.",
            712,
            x=M + 12,
            w=BODY - 24,
            size=9,
            max_h=28,
        )
        self.c.showPage()
        self.c.save()
        return self.buffer.getvalue()


def validate(pdf, draft, group, team, url):
    reader = PdfReader(io.BytesIO(pdf))
    if len(reader.pages) != 3:
        raise ValueError("PDF harus tepat tiga halaman.")
    for page, title in zip(
        reader.pages, ("Informasi proyek", "Video dan bukti 5Vs", "Arsitektur sistem"), strict=True
    ):
        if (
            abs(float(page.mediabox.width) - W) > 0.02
            or abs(float(page.mediabox.height) - H) > 0.02
        ):
            raise ValueError("Halaman harus A4 potret.")
        content = " ".join(page.extract_text().split())
        if title not in content or (DRAFT in content) != draft or (not draft and EMPTY in content):
            raise ValueError("Judul, font, atau label status PDF tidak terverifikasi.")
    page_one = " ".join(reader.pages[0].extract_text().split())
    if any(value and value not in page_one for value in (group, *(v for row in team for v in row))):
        raise ValueError("Identitas tidak terbaca utuh pada PDF.")
    links = [
        [ref.get_object().get("/A", {}).get("/URI") for ref in page.get("/Annots", [])]
        for page in reader.pages
    ]
    if DATASET_PAGE not in links[0] or (url and url not in links[1]) or (not url and links[1]):
        raise ValueError("Tautan PDF tidak cocok dengan data masukan.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--details", type=Path, default=SUB / "submission-data.example.json")
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Project directory containing the verified Complete snapshot.",
    )
    parser.add_argument("--out", type=Path, default=SUB / "generated")
    parser.add_argument("--final", action="store_true", help="Require complete group data.")
    args = parser.parse_args()
    try:
        draft = not args.final
        group, team, url = details(args.details, draft)
        snapshot = EvidenceRepository(Project(args.evidence_root.resolve())).load("complete")
        report = Report(draft)
        report.page_one(snapshot, group, team)
        report.page_two(snapshot, url)
        pdf = report.page_three()
        validate(pdf, draft, group, team, url)
        names = (
            ["VitalFlow_ETS_DRAFT.pdf"]
            if draft
            else [f"{group}_{name}_{nim}.pdf" for name, nim in team]
        )
        if len(set(names)) != len(names) or any(len(name.encode()) > 255 for name in names):
            raise ValueError("Nama berkas final tidak unik atau terlalu panjang.")
        args.out.mkdir(parents=True, exist_ok=not args.final)
        for name in names:
            path = args.out / name
            path.write_bytes(pdf)
            print(f"3 halaman A4 terverifikasi: {path}")
        (args.out / "architecture.svg").write_text(
            renderSVG.drawToString(diagram()), encoding="utf-8"
        )
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f"Gagal membuat PDF: {exc}\n")


if __name__ == "__main__":
    main()
