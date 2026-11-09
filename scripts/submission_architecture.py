"""One vector source for the PDF and the standalone diagram."""

from reportlab.graphics.shapes import Drawing, PolyLine, Rect, String
from reportlab.lib.colors import HexColor, white


def diagram() -> Drawing:
    d = Drawing(503, 476)
    ink, teal, slate = map(HexColor, ("#132B42", "#007870", "#405970"))

    def arrow(points, dashed=False):
        color = slate if dashed else teal
        d.add(
            PolyLine(
                points,
                strokeColor=color,
                strokeWidth=1.25,
                strokeDashArray=[3, 2] if dashed else None,
            )
        )
        (a, b), (x, y) = points[-2:]
        if a == x:
            delta = 5 if b > y else -5
            head = [(x - 3, y + delta), (x, y), (x + 3, y + delta)]
        else:
            delta = 5 if a > x else -5
            head = [(x + delta, y + 3), (x, y), (x + delta, y - 3)]
        d.add(PolyLine(head, strokeColor=color, strokeWidth=1.25))

    def box(x, y, w, kind, title, detail, side=False):
        fill = HexColor("#F0F4F8" if side else "#ECF7F5")
        edge = HexColor("#A3B4C4" if side else "#9BC8C2")
        d.add(Rect(x, y, w, 56, rx=5, ry=5, fillColor=fill, strokeColor=edge, strokeWidth=0.6))
        d.add(
            String(
                x + 12,
                y + 41,
                kind,
                fontName="Helvetica-Bold",
                fontSize=8,
                fillColor=slate if side else teal,
            )
        )
        d.add(String(x + 12, y + 26, title, fontName="Helvetica-Bold", fontSize=11, fillColor=ink))
        d.add(String(x + 12, y + 11, detail, fontName="Helvetica", fontSize=9, fillColor=slate))

    d.add(Rect(0, 0, 503, 476, fillColor=white, strokeColor=None))
    for points in (
        [(128, 416), (128, 405)],
        [(128, 349), (128, 336)],
        [(128, 280), (128, 266)],
        [(364, 280), (364, 271), (242, 271), (242, 238), (230, 238)],
        [(128, 210), (128, 196)],
        [(128, 140), (128, 126)],
        [(26, 168), (12, 168), (12, 28), (26, 28)],
    ):
        arrow(points)
    arrow([(230, 377), (248, 377), (248, 441), (262, 441)], dashed=True)
    arrow([(364, 416), (364, 404)], dashed=True)
    arrow([(466, 376), (484, 376), (484, 28), (466, 28)], dashed=True)
    arrow([(262, 28), (230, 28)], dashed=True)
    arrow([(364, 92), (364, 56)], dashed=True)
    box(26, 416, 204, "01 / SUMBER", "PhysioNet BIDMC 1.0.0", "Numerics.csv dan Fix.txt")
    box(
        26,
        349,
        204,
        "02 / INGESTION",
        "Cache lokal terverifikasi",
        "SHA-256 dan cek struktur berkas",
    )
    box(26, 280, 204, "03A / TRANSFORMASI", "CSV numerik di PySpark", "Tipe, null, dan kunci waktu")
    box(
        262,
        280,
        204,
        "03B / TRANSFORMASI",
        "Fix.txt ke JSON Lines",
        "Metadata terpilih dan skema eksplisit",
    )
    box(
        26, 210, 204, "04 / INTEGRASI", "Join CSV dan JSON", "Banyak observasi ke satu recording_id"
    )
    box(
        26,
        140,
        204,
        "05 / PENYIMPANAN",
        "Parquet dan baca balik",
        "Verifikasi skema dan jumlah baris",
    )
    box(26, 70, 204, "06 / ANALITIK", "Spark SQL", "Ringkasan per rekaman dan menit")
    box(
        26, 0, 204, "07 / KELUARAN", "Dashboard Streamlit", "Ringkasan bukti dan detail via PyArrow"
    )
    box(
        262,
        416,
        204,
        "EKSPERIMEN / VELOCITY",
        "Replay batch historis",
        "CSV bertahap ke inbox lokal",
        side=True,
    )
    box(
        262,
        348,
        204,
        "PENGUKURAN / VELOCITY",
        "Validasi batch di Spark",
        "Interval tiba, antre, proses, total",
        side=True,
    )
    box(
        262,
        92,
        204,
        "UJI TERPISAH / VERACITY",
        "Fixture sintetis",
        "Uji aturan; tidak masuk Parquet",
        side=True,
    )
    box(
        262,
        0,
        204,
        "BUKTI AUDIT & EKSPERIMEN",
        "Arsip run, CSV, JSON, plan",
        "Audit sumber, SQL, Volume, Velocity",
        side=True,
    )
    # Explicit forks from the cache and outputs from the pipeline to the evidence archive.
    arrow([(230, 357), (251, 357), (251, 309), (262, 309)])
    arrow([(230, 98), (248, 98), (248, 41), (262, 41)], dashed=True)
    return d
