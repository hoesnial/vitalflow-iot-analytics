# Walkthrough dashboard · lima menit

**Persiapan:** instal dependensi dan jalankan aplikasi sesuai README. Buka mode **Complete**, cek bahwa Overview menampilkan status pipeline terverifikasi, dan gunakan viewport 1440 × 900. Simpan mode **Fast** untuk memperlihatkan eksekusi pipeline bila diperlukan; kembali ke Complete sebelum membaca bukti. Angka dapat berubah setelah run baru. Bacakan angka yang ada di layar.

| Waktu | Anggota | Urutan dan narasi |
| --- | --- | --- |
| 0:00–0:45 | 1 · Dataset | **Overview.** Sebutkan pertanyaan proyek dan PhysioNet BIDMC. Bedakan jumlah rekaman dari jumlah observasi. Jelaskan kelengkapan sebagai jumlah sel kanal yang terisi pada baris tersimpan. Pilih kanal tren dan arahkan kursor pada satu titik. |
| 0:45–1:40 | 2 · Arsitektur dan Velocity | **System Architecture**: ikuti cache, validasi, join, Parquet, SQL, dan dashboard; tunjukkan replay sebagai cabang eksperimen. **5Vs Lab → Velocity**: klik **Mulai replay** atau **Langkah berikutnya**. Bedakan target interval, interval kedatangan terukur, waktu Spark, waktu antre, dan total latensi. Katakan bahwa ini replay data historis. |
| 1:40–2:40 | 3 · Variety dan Veracity | **Variety**: bandingkan skema CSV dan JSON, tunjukkan recording ID dan jumlah baris sebelum/sesudah join. **Veracity**: tampilkan kehilangan data dan timestamp negatif dari sumber resmi. Jika menampilkan fixture, sebutkan bahwa ini uji terpisah dan tidak masuk ke analitik. |
| 2:40–3:45 | 4 · Volume dan performa | **Volume**: bandingkan group/count dengan join dan jendela waktu. Buka **Per percobaan** atau physical plan. Sebutkan input yang sama, grup keluaran yang berbeda, dan kerja tambahan Spark. Data kecil dan timing lokal tidak membuktikan skalabilitas klaster. |
| 3:45–5:00 | 5 · Value | **Value**: pilih RESP dan periksa insight kelengkapan. Bandingkan jendela lengkap pada `bidmc_01` jika tersedia. Opsional: **Recording Explorer → bidmc_13 → RESP** untuk melihat celah pengukuran. Akhiri dengan batasan: observasional, historis, bukan diagnosis. |

**Jika replay otomatis tidak nyaman untuk rekaman layar:** klik **Jeda**, lalu **Langkah berikutnya** untuk menampilkan batch berikutnya. **Reset** kembali ke posisi nol. Seluruh tombol hanya mengubah tampilan dan tidak menyentuh sumber atau hasil eksperimen.

**Untuk evaluator:** **Evidence & Methodology** menunjukkan versi dataset, manifest dan SHA-256, versi Spark, ringkasan QA bila tersedia, dan artefak rubrik yang dapat diunduh. Jangan tampilkan isi Fix.txt mentah. Sebutkan bahwa durasi lokal tidak mengukur latensi sensor dan bahwa kelengkapan bukan uptime.

Panduan ini belum mencakup pembuatan video atau PDF final.
