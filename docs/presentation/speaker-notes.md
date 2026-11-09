# Catatan pembicara dan tanya jawab

| Peran | Pegangan saat menjelaskan | Jika evaluator bertanya |
| --- | --- | --- |
| 1 · M1 | Satu baris adalah pengamatan pada waktu relatif; satu rekaman berisi banyak baris. | 53 rekaman tidak berarti 53 pasien unik. Cakupan proyek: Numerics dan Fix, bukan sinyal 125 Hz. |
| 2 · M2 | Cache memverifikasi SHA-256; Parquet dan artefak berasal dari pipeline batch. | Spark lokal memberi akses ke operasi dan plan yang sama jenisnya dengan Spark klaster, tetapi tidak menguji distribusi antar mesin. Replay bercabang dari cache. |
| 3 · M3–M4 | Bedakan null, nol, waktu negatif, dan duplikat. JSON adalah metadata hasil turunan. | HDFS adalah materi M4; penyimpanan lokal dipilih karena skala kecil. Berkas Fix mentah tidak ditampilkan. Fixture hanya menguji aturan dan tidak masuk Parquet. |
| 4 · M5–M6 | Jelaskan pola agregasi parsial, pertukaran partisi, dan agregasi akhir; join memakai broadcast metadata. | Ini konsep yang berhubungan dengan MapReduce, dijalankan oleh Spark, tanpa job Hadoop MapReduce. Durasi benchmark lokal mencakup materialisasi dan collect; bandingkan bentuk operasi, bukan klaim kecepatan universal. Throughput Spark aktif berbeda dari frekuensi batch. |
| 5 · M7 | Saat membaca rata-rata, sebutkan penyebutnya. Bandingkan hanya jendela yang cakupannya jelas. | 335/481 RESP adalah kelengkapan rekaman tersebut. Perubahan HR tidak menjelaskan penyebab dan tidak berlaku untuk populasi pasien. |
