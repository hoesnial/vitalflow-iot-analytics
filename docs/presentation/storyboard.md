# Storyboard · lima pembicara

Gunakan 1440 × 900 untuk menangkap UI; keluarkan ke kanvas 1920 × 1080 dengan crop yang mempertahankan label dan satuan. Siapkan klip sesuai urutan agar jeda antarhalaman bisa dipotong. Nomor cue mengacu pada [naskah](video-script.md).

| Cue / waktu rencana | Tampilan dan tindakan | Bukti yang harus terbaca |
| --- | --- | --- |
| 1A · 00:00–00:21 | Overview → biarkan Complete; arahkan kursor ke grafik HR | Judul, badge PhysioNet, dan tren contoh |
| 1B · 00:21–00:45 | Overview → tunjuk kartu jumlah; sorot label sumber | 53 rekaman, 25.492 observasi tersimpan, kelengkapan 99,59 persen |
| 2A · 00:45–01:10 | System Architecture → ikuti panah utama dari kiri; pilih Penyimpanan Parquet | Cache, parsing, integrasi, Parquet, Spark SQL, dashboard |
| 2B · 01:10–01:30 | 5Vs Lab → Velocity; tunjuk label replay dan target interval | Historical Dataset Replay dan target 1 detik |
| 3A · 01:30–01:59 | 5Vs Lab → Variety → Bandingkan skema sumber; buka Metadata JSON dan contoh hasil join | Numerics CSV, metadata JSON Lines, kunci, sampel hasil join |
| 3B · 01:59–02:30 | Veracity → Sumber PhysioNet; pindah ke Fixture sintetis | Temuan sumber dan hasil uji sintetis di tampilan berbeda |
| 4A · 02:30–02:53 | Sisipkan klip eksekusi Fast; potong ke Complete → Volume → Median | Log pemrosesan Fast berlabel, lalu dua operasi dan grup Complete |
| 4B · 02:53–03:16 | Volume → Skema CSV dan Spark physical plan → pilih operasi B; sorot BroadcastHashJoin dan Exchange | Rencana fisik, lalu median pada grafik |
| 4C · 03:16–03:45 | Velocity → Reset → Mulai replay; berhenti atau jeda setelah tabel terlihat | Enam batch, waktu tiba dan selesai, interval, durasi Spark dan baris/detik |
| 5A · 03:45–04:12 | Sisipkan klip kueri SQL → Value → RESP; pilih bidmc_13 | Query SQL dan hitungan valid; panel insight RESP |
| 5B · 04:12–04:36 | Recording Explorer → bidmc_13 → RESP; aktifkan Tandai nilai hilang | Garis terputus dan penanda kuning di baris terpisah |
| 5C · 04:36–04:55 | Value → bandingkan jendela lengkap pertama dan terakhir; tahan hingga 04:55 | bidmc_01: 60 bacaan tiap kanal per jendela; HR sekitar 93,08 dan 90,70 |
| Penutup · 04:55–05:00 | Tahan panel hasil atau tampilkan kartu sumber tanpa narasi baru | PhysioNet BIDMC v1.0.0; 5Vs dan batas studi |

Letakkan teks overlay di luar judul grafik, tooltip, sumbu waktu, dan panel status. Labeli klip Fast sebagai **3 rekaman / cuplikan eksekusi**; semua angka utama memakai Complete.
