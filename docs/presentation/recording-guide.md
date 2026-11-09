# Panduan rekam VitalFlow

Mulai dari direktori repo. Pasang dependensi sebelum hari rekam, lalu cek snapshot lokal tanpa unduhan baru.

```sh
.venv/bin/python -m pip install -e '.[dashboard,dev,submission]'
.venv/bin/python scripts/demo_readiness.py
.venv/bin/python -m streamlit run dashboard/app.py --server.headless true --server.port 8512
```

Buka [dashboard lokal](http://127.0.0.1:8512) pada 1440 × 900, zoom browser 100%, dan pilih **Complete**. Tes dua halaman awal dengan jaringan dimatikan. Pastikan semua klip menggunakan snapshot yang sama. Cek tab dan notifikasi pribadi sebelum mulai merekam.

Siapkan dua klip eksekusi sebelum merekam narasi. Jalankan dari direktori repo dengan Java tersedia. Tampilkan perintah dan hasilnya; potong waktu tunggu. Hindari nama akun, direktori pribadi, URL internal, isi Fix mentah, dan terminal dengan riwayat pribadi.

```sh
# Segmen 4: run Fast di direktori sementara agar semua snapshot demo tetap utuh.
audit_dir=$(mktemp -d /tmp/vitalflow-video.XXXXXX)
ln -s "$PWD/data" "$audit_dir/data"
VITALFLOW_AUDIT_ROOT="$audit_dir" .venv/bin/python -c '
import os
from pathlib import Path
from vitalflow.config import Project
from vitalflow.pipeline import RunOptions, run
from vitalflow.spark import session

s = session()
try:
    result = run(s, Project(Path(os.environ["VITALFLOW_AUDIT_ROOT"])), RunOptions(3))
    print({k: result[k] for k in ("recording_count", "source_rows", "parquet_readback_rows")})
finally:
    s.stop()
'

# Segmen 5: kueri Spark SQL atas Parquet Complete; tanpa menjalankan pipeline.
.venv/bin/python scripts/demo_readiness.py --query
```

Rekam dalam urutan [storyboard](storyboard.md): Overview → arsitektur dan pengantar replay → Variety dan Veracity → Volume dan replay terukur → Value dan Explorer. Di Velocity, gunakan **Reset → Mulai replay**, atau **Langkah berikutnya** bila ingin menahan satu batch. Jika browser perlu muat ulang, kembali ke Complete, buka halaman yang sama, dan potong jedanya. Hasil Spark berasal dari arsip; kontrol replay tidak menulis data.

Rekam layar dan audio per anggota, sesuaikan level audio, lalu satukan. Target durasi akhir 04:55–05:00. Sinkronkan [transkrip](subtitle-transcript.md) dengan audio aktual, ekspor closed captions Bahasa Indonesia, lalu unggah video dan caption melalui akun kelompok. Uji akses penonton tanpa akun kelompok sebelum memasukkan URL ke PDF.
