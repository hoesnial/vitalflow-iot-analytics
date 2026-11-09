# VitalFlow · laporan kesiapan ETS IFB-451

**9 November 2026, WIB.** Prototipe dan paket produksi video siap digunakan. PDF yang tersedia adalah **DRAF**. Penyelesaian pengumpulan bergantung pada rekaman lima anggota, closed captions, URL video yang dapat diakses, nomor kelompok, lima nama lengkap, dan lima NIM. Tenggat dalam dokumen ETS adalah **10 November 2026**.

| Pemeriksaan | Status | Hasil |
| --- | --- | --- |
| Ketentuan universitas | PASS | Meninjau PDF ETS IFB-451, termasuk tabel 3.1, 7.1, bagian 9 dan tabel 10.1, serta modul M1–M7. Lampiran IFB-451 pengganti identik byte per byte. IFB-499 adalah mata kuliah berbeda. |
| Integritas sumber | PASS | Verifikasi cache offline: 106 berkas resmi, 53 pasangan, 462.700 byte di luar manifest. Pipeline hanya menggunakan cache pada run audit. |
| Pipeline lokal dan reproduksibilitas | PASS | Eksekusi Fast dan Complete di direktori sementara memakai cache yang sama. Fast: 1.443 baris dari sumber hingga readback. Complete: 25.493 → 25.492 setelah validasi dan tetap 25.492 pada readback. Sembilan ekspor stabil identik byte per byte dengan snapshot Complete dashboard. |
| Data, kualitas, provenance | PASS | 413 sel kosong dipertahankan sebagai null; satu waktu negatif dikeluarkan; tidak ada kunci valid berulang pada sumber. Fixture 8 → 3 baris tetap terpisah. Kelengkapan 99,59% memakai penyebut 25.492 baris × empat kanal. |
| Spark SQL dan demo | PASS | Pemeriksaan persiapan membaca Parquet serta kedua plan. Kueri demo aktual dari Parquet menghasilkan 335 dari 481 RESP valid dan rerata 3,7104; sama dengan ekspor Spark SQL. |
| Tes, format, dependensi | PASS | 31 pytest lulus (16 pipeline, 15 dashboard), Ruff lint dan format lulus, `pip check` lulus. Python 3.12.14, Spark 4.2.1, Java 25.0.4.1. |
| Dashboard dan browser | PASS | Health endpoint aktif. Walkthrough penuh Chrome/Playwright pada 1440 × 900 dan 1280 × 720 tanpa akses eksternal, termasuk semua mode, navigasi, gap, toggle, reset, perbandingan kanal, replay, unduhan, atribusi sumber, dan cek overflow/galat browser. Overview juga diuji pada 390 × 844. Tautan PhysioNet diperiksa terpisah. |
| Rubrik teknis dan interpretasi | PASS | [Audit](final-rubric-audit.md) memetakan semua kriteria ke kode, eksperimen dan bukti; pelaksanaan presentasi dinilai terpisah. |
| PDF draf dan ilustrasi | PASS | Draf berlabel tiap halaman; PDF tepat tiga halaman A4 potret (595,276 × 841,89 pt). Anotasi PhysioNet valid; ketiga render diperiksa untuk keterbacaan dan penempatan. Diagram vektor diekspor ke SVG. Mode final menolak JSON kosong dan tidak menulis berkas. |
| Video dan caption aktual | PARTIAL | Enam dokumen produksi tersedia. Audio lima presenter, durasi, timing caption, dan akses penonton perlu diuji pada video aktual. |
| Lima PDF final | BLOCKED | Nomor kelompok, nama/NIM kelima anggota, dan URL YouTube belum tersedia. Tidak ada PDF final yang dibuat. |
| Akses URL video dan pengumpulan | NOT TESTED | Validasi anotasi YouTube dan nama berkas individual dijalankan generator saat input nyata tersedia; uji akses video dari jendela privat dan pengumpulan dilakukan oleh kelompok. |

Dashboard, draf, dan naskah mengacu pada **snapshot Complete yang dipublikasikan 7 November 2026 pukul 14:12:28 WIB**. Run audit 9 November dibuat di luar folder keluaran demo: hasil stabil cocok, waktu berbeda. Median tiba hingga selesai 228,9 ms pada snapshot demo dan 194,3 ms pada run audit. Kedua angka adalah ukuran lokal. Hindari mengganti snapshot antara perekaman video dan pembuatan PDF; jika diulang, cocokkan kembali angka naskah dengan UI dan draf.

## Perintah yang diverifikasi

Dijalankan dari direktori VitalFlow, dengan venv yang sudah tersedia. `NODE_PATH` menunjuk ke instalasi Playwright QA lokal.

```sh
.venv/bin/python -m pip install 'reportlab==4.4.4' 'pypdf==6.12.2'
.venv/bin/python -m pip check
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest -q --junitxml=outputs/dashboard-qa/pytest.xml
.venv/bin/python -m vitalflow download --mode complete --offline
.venv/bin/python -m streamlit run dashboard/app.py --server.headless true --server.port 8512
# Jalankan perintah di bawah dari terminal kedua.
curl -fsS http://127.0.0.1:8512/_stcore/health
NODE_PATH=/tmp/vitalflow-browser.E9RwnS/node_modules node scripts/dashboard_browser_qa.cjs
.venv/bin/python scripts/demo_readiness.py
.venv/bin/python scripts/demo_readiness.py --query
.venv/bin/python scripts/generate_submission.py
pdfinfo docs/submission/generated/VitalFlow_ETS_DRAFT.pdf
pdftoppm -r 112 -png docs/submission/generated/VitalFlow_ETS_DRAFT.pdf outputs/submission-qa/page
# Harus keluar 1 tanpa membuat direktori.
.venv/bin/python scripts/generate_submission.py --final --details docs/submission/submission-data.example.json --out outputs/submission-qa/unfilled-final
```

Untuk run audit pipeline tanpa menimpa snapshot demo:

```sh
audit_dir=$(mktemp -d /tmp/vitalflow-release.XXXXXX)
ln -s "$PWD/data" "$audit_dir/data"
export VITALFLOW_AUDIT_ROOT="$audit_dir"
export JAVA_HOME="$(/usr/libexec/java_home -v 25)"
.venv/bin/python -c 'import os; from pathlib import Path; from vitalflow.config import Project; from vitalflow.pipeline import RunOptions, run; from vitalflow.spark import session; s=session(); p=Project(Path(os.environ["VITALFLOW_AUDIT_ROOT"])); print(run(s,p,RunOptions(3))); print(run(s,p,RunOptions(53))); s.stop()' > "$audit_dir/pipeline.log" 2>&1
for f in analytics/by_recording.csv analytics/by_minute.csv integration.json source_schema.json quality/source.json quality/controlled_fixture.json quality/time_coverage.csv data/metadata/recordings.jsonl provenance.json; do
  cmp "outputs/53-recordings/$f" "$audit_dir/outputs/53-recordings/$f" || exit 1
done
```

Log lokal: `outputs/dashboard-qa/pytest.xml`, `outputs/dashboard-qa/iteration-03-browser.log`, tangkapan layar di `outputs/dashboard-qa/screenshots/`, dan render PDF di `outputs/submission-qa/`. Ikuti [panduan rekam](presentation/recording-guide.md) lalu [panduan PDF final](submission/submission-template.md). Data observasional tidak mendukung klaim klinis; Spark satu mesin tidak mendukung klaim skalabilitas klaster.
