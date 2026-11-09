# Transkrip untuk closed captions (Bahasa Indonesia)

Cue diurutkan menurut storyboard. Waktu adalah **rencana**, belum sinkron dengan rekaman. Pecah tiap paragraf ke caption pendek mengikuti audio, ganti angka ejaan menjadi angka jika membantu keterbacaan, lalu ekspor SRT dari editor setelah timing final. Jangan unggah rentang blok ini sebagai timing final.

## 1 · Project Lead / Analyst (M1)

**1A · 00:00–00:21 (rencana)**

Di layar monitor, garis yang terlihat rapi belum tentu berasal dari pembacaan yang lengkap. VitalFlow menjawab satu pertanyaan: selama satu rekaman, bagaimana nilai dan ketersediaan denyut jantung, nadi, laju napas, dan saturasi oksigen berubah? Kami menampilkan tren bersama jumlah pembacaan yang benar-benar tersedia.

**1B · 00:21–00:45 (rencana)**

Kami memakai lima puluh tiga rekaman historis BIDMC dari PhysioNet. Ada dua puluh lima ribu empat ratus sembilan puluh tiga baris numerik, plus satu metadata per rekaman. Volume menentukan cara memproses, Velocity cara menguji kedatangan, Variety cara menggabungkan, Veracity cara memvalidasi, dan Value cara membaca hasil. Mari ikuti alurnya.

## 2 · System Engineer (M2)

**2A · 00:45–01:10 (rencana)**

Kami memeriksa sidik jari berkas dari PhysioNet sebelum menyimpannya di cache. Spark membaca observasi dan metadata, memvalidasi keduanya, lalu menggabungkannya. Hasil disimpan sebagai Parquet, dibaca kembali, dan diringkas dengan Spark SQL. Spark lokal cukup untuk ukuran data ini dan memungkinkan kami melihat rencana eksekusinya. Dashboard membuka hasil yang sudah tersimpan.

**2B · 01:10–01:30 (rencana)**

Replay berjalan sebagai cabang terpisah. Produsen lokal mengirim potongan data historis ke folder masuk dengan target satu detik antarbatch. Spark memproses batch yang tiba, dan kami mencatat waktunya. Dashboard memutar kembali catatan tersebut. Sekarang kita lihat apa yang sebenarnya masuk ke Spark.

## 3 · Data Engineer (M3–M4)

**3A · 01:30–01:59 (rencana)**

CSV numerik berisi waktu relatif dan empat pengukuran. Dari Fix TXT, kami mengambil metadata terpilih seperti lokasi dan frekuensi sampel, lalu membentuk JSON Lines dengan skema tersendiri. Kuncinya adalah ID rekaman. Banyak observasi dapat bertemu satu metadata. Pemeriksaan kunci memastikan tidak ada baris yang kehilangan pasangan atau bertambah saat join. Parquet menyimpan hasil dengan tipe kolom yang diperiksa saat baca balik.

**3B · 01:59–02:30 (rencana)**

Pada sumber asli, ada empat ratus tiga belas sel pengukuran kosong dan satu waktu negatif. Baris dengan waktu negatif dikeluarkan karena waktunya tidak sah. Sel kosong tetap null. Tidak ada kunci waktu berulang pada sumber. Untuk menguji aturan duplikat, kami pakai fixture terpisah: dari delapan baris, dua gagal aturan waktu dan tiga merupakan duplikat yang dibuang. Hasil uji ini tidak masuk ke analitik. Berikutnya, kita bandingkan kerja Spark.

## 4 · Big Data Developer (M5–M6)

**4A · 02:30–02:53 (rencana)**

Cuplikan ini memperlihatkan PySpark memproses mode Fast. Untuk membandingkan performa, kita kembali ke hasil Complete. Operasi A menghitung baris per rekaman. Operasi B memakai observasi yang sama, menambahkan join metadata, lalu mengelompokkan menurut rekaman, lokasi, dan jendela satu menit. Hasilnya lima puluh tiga grup dibanding empat ratus tujuh puluh enam.

**4B · 02:53–03:16 (rencana)**

Rencana fisik memperlihatkan Spark menyiarkan metadata kecil ke pekerja dan mendistribusikan ulang baris untuk agregasi. Setelah pemanasan, median tiga percobaan sekitar tujuh belas dan dua puluh satu milidetik. Selisih ini terkait bentuk operasi dan pengelompokan pada mesin ini. Pengukuran lokal tidak membuktikan performa klaster.

**4C · 03:16–03:45 (rencana)**

Untuk Velocity, lihat kapan batch tiba dan selesai, bukan waktu query tadi. Pada enam batch, jeda kedatangan terukur mendekati satu detik dan median dari tiba sampai selesai sekitar dua ratus dua puluh sembilan milidetik. Laju per batch adalah jumlah baris dibagi waktu baca dan proses Spark. Ini eksperimen historis lokal, bukan latensi alat medis. Sekarang, apa manfaat hasilnya?

## 5 · Data Analyst (M7)

**5A · 03:45–04:12 (rencana)**

Kueri Spark SQL membaca Parquet dan menghitung rata-rata serta jumlah bacaan valid per rekaman dan per menit. Pada rekaman BIDMC tiga belas, hanya tiga ratus tiga puluh lima dari empat ratus delapan puluh satu bacaan napas yang valid. Kalau hanya melihat rata-rata, kita bisa melewatkan fakta bahwa hampir sepertiga bacaan tidak tersedia.

**5B · 04:12–04:36 (rencana)**

Di Explorer, garis laju napas terputus saat nilai hilang, dan penandanya dipisahkan dari sumbu nilai. Nol yang tercatat tetap terlihat sebagai nol. Bagi peninjau data monitor, ini membantu menentukan kanal dan interval yang perlu diperiksa sebelum mempercayai tren. Penyebab celahnya tidak bisa disimpulkan dari rekaman ini.

**5C · 04:36–04:55 (rencana)**

Pada BIDMC satu, rata-rata denyut jantung pada menit lengkap pertama sekitar sembilan puluh tiga dan pada menit lengkap terakhir sekitar sembilan puluh satu. Keduanya punya cakupan yang sama. Kesimpulannya: baca nilai bersama kelengkapannya. Temuan ini terbatas pada rekaman historis, bukan diagnosis.
