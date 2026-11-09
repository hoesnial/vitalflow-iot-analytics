# Naskah video VitalFlow · IFB-451

Rekam lima segmen sesuai pembagian resmi. Target baca sekitar **130–145 kata/menit**; angka sudah dieja untuk estimasi. Rentang adegan adalah jatah, bukan waktu subtitle. Rekam percobaan dan ukur durasi sebenarnya. Tahan layar hingga batas segmen jika narasi selesai dulu. Sisakan 04:55–05:00 untuk penutup dan potong video pada atau sebelum 05:00.

Gunakan snapshot Complete bertanggal **7 November 2026, 14:12 WIB**. Angka performa merujuk run itu; jika snapshot diulang, cocokkan grafik, narasi, subtitle dan PDF sebelum merekam. Bukti di bawah relatif terhadap `outputs/53-recordings/` kecuali cuplikan Fast.

## 00:00–00:45 · 1 · Project Lead / Analyst (M1)

92 kata; sekitar 38–42 detik bicara.

**1A · 00:00–00:21 (jatah 21 detik).** Overview → biarkan Complete; arahkan kursor ke grafik HR. Layar: Judul, badge PhysioNet, dan tren contoh. Bukti: `run.json`, `provenance.json`, `analytics/by_minute.csv`.

> Di layar monitor, garis yang terlihat rapi belum tentu berasal dari pembacaan yang lengkap. VitalFlow menjawab satu pertanyaan: selama satu rekaman, bagaimana nilai dan ketersediaan denyut jantung, nadi, laju napas, dan saturasi oksigen berubah? Kami menampilkan tren bersama jumlah pembacaan yang benar-benar tersedia.

**1B · 00:21–00:45 (jatah 24 detik).** Overview → tunjuk kartu jumlah; sorot label sumber. Layar: 53 rekaman, 25.492 observasi tersimpan, kelengkapan 99,59 persen. Bukti: `run.json`, `provenance.json`, `quality/source.json`.

> Kami memakai lima puluh tiga rekaman historis BIDMC dari PhysioNet. Ada dua puluh lima ribu empat ratus sembilan puluh tiga baris numerik, plus satu metadata per rekaman. Volume menentukan cara memproses, Velocity cara menguji kedatangan, Variety cara menggabungkan, Veracity cara memvalidasi, dan Value cara membaca hasil. Mari ikuti alurnya.

## 00:45–01:30 · 2 · System Engineer (M2)

92 kata; sekitar 38–42 detik bicara.

**2A · 00:45–01:10 (jatah 25 detik).** System Architecture → ikuti panah utama dari kiri; pilih Penyimpanan Parquet. Layar: Cache, parsing, integrasi, Parquet, Spark SQL, dashboard. Bukti: `provenance.json`, `integration.json`, `run.json`.

> Kami memeriksa sidik jari berkas dari PhysioNet sebelum menyimpannya di cache. Spark membaca observasi dan metadata, memvalidasi keduanya, lalu menggabungkannya. Hasil disimpan sebagai Parquet, dibaca kembali, dan diringkas dengan Spark SQL. Spark lokal cukup untuk ukuran data ini dan memungkinkan kami melihat rencana eksekusinya. Dashboard membuka hasil yang sudah tersimpan.

**2B · 01:10–01:30 (jatah 20 detik).** 5Vs Lab → Velocity; tunjuk label replay dan target interval. Layar: Historical Dataset Replay dan target 1 detik. Bukti: `benchmarks/velocity.json`, `benchmarks/velocity_batches.csv`.

> Replay berjalan sebagai cabang terpisah. Produsen lokal mengirim potongan data historis ke folder masuk dengan target satu detik antarbatch. Spark memproses batch yang tiba, dan kami mencatat waktunya. Dashboard memutar kembali catatan tersebut. Sekarang kita lihat apa yang sebenarnya masuk ke Spark.

## 01:30–02:30 · 3 · Data Engineer (M3–M4)

129 kata; sekitar 53–60 detik bicara.

**3A · 01:30–01:59 (jatah 29 detik).** 5Vs Lab → Variety → Bandingkan skema sumber; buka Metadata JSON dan contoh hasil join. Layar: Numerics CSV, metadata JSON Lines, kunci, sampel hasil join. Bukti: `source_schema.json`, `data/metadata/recordings.jsonl`, `integration.json`.

> CSV numerik berisi waktu relatif dan empat pengukuran. Dari Fix TXT, kami mengambil metadata terpilih seperti lokasi dan frekuensi sampel, lalu membentuk JSON Lines dengan skema tersendiri. Kuncinya adalah ID rekaman. Banyak observasi dapat bertemu satu metadata. Pemeriksaan kunci memastikan tidak ada baris yang kehilangan pasangan atau bertambah saat join. Parquet menyimpan hasil dengan tipe kolom yang diperiksa saat baca balik.

**3B · 01:59–02:30 (jatah 31 detik).** Veracity → Sumber PhysioNet; pindah ke Fixture sintetis. Layar: Temuan sumber dan hasil uji sintetis di tampilan berbeda. Bukti: `quality/source.json`, `quality/controlled_fixture.json`.

> Pada sumber asli, ada empat ratus tiga belas sel pengukuran kosong dan satu waktu negatif. Baris dengan waktu negatif dikeluarkan karena waktunya tidak sah. Sel kosong tetap null. Tidak ada kunci waktu berulang pada sumber. Untuk menguji aturan duplikat, kami pakai fixture terpisah: dari delapan baris, dua gagal aturan waktu dan tiga merupakan duplikat yang dibuang. Hasil uji ini tidak masuk ke analitik. Berikutnya, kita bandingkan kerja Spark.

## 02:30–03:45 · 4 · Big Data Developer (M5–M6)

152 kata; sekitar 63–70 detik bicara.

**4A · 02:30–02:53 (jatah 23 detik).** Sisipkan klip eksekusi Fast; potong ke Complete → Volume → Median. Layar: Log pemrosesan Fast berlabel, lalu dua operasi dan grup Complete. Bukti: `run.json`, `benchmarks/volume.json`.

> Cuplikan ini memperlihatkan PySpark memproses mode Fast. Untuk membandingkan performa, kita kembali ke hasil Complete. Operasi A menghitung baris per rekaman. Operasi B memakai observasi yang sama, menambahkan join metadata, lalu mengelompokkan menurut rekaman, lokasi, dan jendela satu menit. Hasilnya lima puluh tiga grup dibanding empat ratus tujuh puluh enam.

**4B · 02:53–03:16 (jatah 23 detik).** Volume → Skema CSV dan Spark physical plan → pilih operasi B; sorot BroadcastHashJoin dan Exchange. Layar: Rencana fisik, lalu median pada grafik. Bukti: `benchmarks/aggregation_plan.txt`, `benchmarks/join_and_window_plan.txt`, `benchmarks/volume.json`.

> Rencana fisik memperlihatkan Spark menyiarkan metadata kecil ke pekerja dan mendistribusikan ulang baris untuk agregasi. Setelah pemanasan, median tiga percobaan sekitar tujuh belas dan dua puluh satu milidetik. Selisih ini terkait bentuk operasi dan pengelompokan pada mesin ini. Pengukuran lokal tidak membuktikan performa klaster.

**4C · 03:16–03:45 (jatah 29 detik).** Velocity → Reset → Mulai replay; berhenti atau jeda setelah tabel terlihat. Layar: Enam batch, waktu tiba dan selesai, interval, durasi Spark dan baris/detik. Bukti: `benchmarks/velocity.json`, `benchmarks/velocity_batches.csv`.

> Untuk Velocity, lihat kapan batch tiba dan selesai, bukan waktu query tadi. Pada enam batch, jeda kedatangan terukur mendekati satu detik dan median dari tiba sampai selesai sekitar dua ratus dua puluh sembilan milidetik. Laju per batch adalah jumlah baris dibagi waktu baca dan proses Spark. Ini eksperimen historis lokal, bukan latensi alat medis. Sekarang, apa manfaat hasilnya?

## 03:45–05:00 · 5 · Data Analyst (M7)

139 kata; sekitar 58–64 detik bicara.

**5A · 03:45–04:12 (jatah 27 detik).** Sisipkan klip kueri SQL → Value → RESP; pilih bidmc_13. Layar: Query SQL dan hitungan valid; panel insight RESP. Bukti: `analytics/by_recording.csv`, `analytics/by_minute.csv`.

> Kueri Spark SQL membaca Parquet dan menghitung rata-rata serta jumlah bacaan valid per rekaman dan per menit. Pada rekaman BIDMC tiga belas, hanya tiga ratus tiga puluh lima dari empat ratus delapan puluh satu bacaan napas yang valid. Kalau hanya melihat rata-rata, kita bisa melewatkan fakta bahwa hampir sepertiga bacaan tidak tersedia.

**5B · 04:12–04:36 (jatah 24 detik).** Recording Explorer → bidmc_13 → RESP; aktifkan Tandai nilai hilang. Layar: Garis terputus dan penanda kuning di baris terpisah. Bukti: `data/processed/observations.parquet`, `analytics/by_recording.csv`.

> Di Explorer, garis laju napas terputus saat nilai hilang, dan penandanya dipisahkan dari sumbu nilai. Nol yang tercatat tetap terlihat sebagai nol. Bagi peninjau data monitor, ini membantu menentukan kanal dan interval yang perlu diperiksa sebelum mempercayai tren. Penyebab celahnya tidak bisa disimpulkan dari rekaman ini.

**5C · 04:36–04:55 (jatah 19 detik).** Value → bandingkan jendela lengkap pertama dan terakhir; tahan hingga 04:55. Layar: bidmc_01: 60 bacaan tiap kanal per jendela; HR sekitar 93,08 dan 90,70. Bukti: `analytics/by_minute.csv`.

> Pada BIDMC satu, rata-rata denyut jantung pada menit lengkap pertama sekitar sembilan puluh tiga dan pada menit lengkap terakhir sekitar sembilan puluh satu. Keduanya punya cakupan yang sama. Kesimpulannya: baca nilai bersama kelengkapannya. Temuan ini terbatas pada rekaman historis, bukan diagnosis.
