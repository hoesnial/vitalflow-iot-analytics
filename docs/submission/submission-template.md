# VitalFlow · lembar pengisian PDF ETS

Generator membaca JSON identitas, bukan Markdown ini. Salin [contoh JSON](submission-data.example.json) ke `docs/submission/submission-data.json`. Isi nomor kelompok, lima nama lengkap dan NIM sebagai string, dengan urutan anggota sama seperti urutan video, lalu tempel URL YouTube sebenarnya. Berkas identitas dan keluaran generator diabaikan Git.

1. **Informasi proyek:** VitalFlow, Itenas, IFB-451, tabel anggota, masalah pemantauan, tujuan dan sumber BIDMC versi 1.0.0.
2. **Video dan 5Vs:** tautan video, ringkasan metrik dan interpretasi. Metrik dibaca dari snapshot Complete melalui validator dashboard, tanpa rerun Spark.
3. **Arsitektur:** ilustrasi vektor dari [sumber diagram](../../scripts/submission_architecture.py), diekspor sebagai `architecture.svg` bersama PDF.

```sh
.venv/bin/python -m pip install -e '.[dashboard,submission]'
.venv/bin/python scripts/generate_submission.py
cp -n docs/submission/submission-data.example.json docs/submission/submission-data.json
# Setelah mengisi JSON dan menguji pemutaran video:
.venv/bin/python scripts/generate_submission.py --final \
  --details docs/submission/submission-data.json --out docs/submission/generated/final
```

Mode default selalu menghasilkan draf berlabel pada setiap halaman. Mode final menolak input yang belum lengkap dan direktori keluaran yang sudah ada; untuk revisi pilih direktori baru. Mode final menulis lima PDF dengan isi identik dan nama `GroupNumber_FullName_NIM.pdf`. Generator mengecek ukuran, judul, isi identitas dan anotasi tautan. Tautan yang valid secara format belum membuktikan bahwa video sudah dapat diakses.

Untuk tiap versi final, jalankan `pdfinfo` pada berkas PDF dan pastikan tiga halaman A4, lalu render satu PDF (isi kelimanya sama) dengan `pdftoppm -r 112 -png`. Baca ulang seluruh nama, NIM, tabel, dan diagram pada hasil render. Klik URL dari PDF dan uji video serta caption di jendela privat. Cocokkan metrik dengan layar Complete yang dipakai dalam video. Setiap anggota mengunggah PDF dengan nama dirinya sendiri. Jangan gunakan draf untuk pengumpulan.
