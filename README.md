# VitalFlow

## Panduan cepat menjalankan (Bahasa Indonesia)

Gunakan Python 3.12 dan Java 25. Setelah mengunduh repositori, buka Terminal di folder VitalFlow (`cd` ke folder hasil clone). Contoh untuk pengguna baru:

```sh
git clone https://github.com/hoesnial/vitalflow-iot-analytics.git
cd vitalflow-iot-analytics
python3.12 --version
java -version
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dashboard,dev,submission]'
```

Jika Anda sudah memiliki folder proyek, cukup buka folder itu di Terminal, aktifkan `.venv` (buat dahulu jika belum ada), lalu jalankan perintah instalasi. Pada macOS dengan beberapa JDK, pilih Java 25 melalui `export JAVA_HOME="$(/usr/libexec/java_home -v 25)"` sebelum menjalankan pipeline. Dashboard membaca hasil pipeline dari `outputs/`.

Periksa apakah bukti Complete sudah ada:

```sh
python scripts/demo_readiness.py
```

Jika pemeriksaan berhasil, langsung jalankan dashboard. Jika belum, unduh dan proses dataset seperti di bawah.

Perintah `download` mengambil dataset resmi PhysioNet, memeriksa SHA-256, dan menyimpan 53 pasang berkas Numerics.csv dan Fix.txt di `data/raw/bidmc/1.0.0/`. Perintah `run` membaca cache lokal dan membuat bukti untuk dashboard di `outputs/53-recordings/`:

```sh
vitalflow download --mode complete   # perlu internet saat unduhan pertama
vitalflow run --mode complete        # memakai cache lokal; memerlukan Java/Spark
python scripts/demo_readiness.py
```

Jalankan dashboard dari folder proyek dengan `.venv` aktif:

```sh
python -m streamlit run dashboard/app.py --server.headless true --server.port 8512
```

Buka [http://127.0.0.1:8512](http://127.0.0.1:8512). Untuk menghentikan server, tekan `Ctrl+C` di Terminal. Jika port 8512 sudah dipakai oleh VitalFlow, cukup buka tautan tersebut.

Untuk mencoba lebih cepat, gunakan `--mode fast` pada perintah `download` dan `run` (3 rekaman), kemudian pilih **Fast** di sidebar dashboard. Mode **Default** memakai 10 rekaman; **Complete** memakai 53 rekaman dan menjadi sumber utama demo. Setiap mode memiliki hasil sendiri di `outputs/03-recordings/`, `outputs/10-recordings/`, atau `outputs/53-recordings/`. Dataset tidak diunggah lewat halaman dashboard. Setelah unduhan pertama, `vitalflow download --mode complete --offline` dapat memeriksa cache tanpa internet. Jika menerima ZIP folder `outputs` dari rekan, ekstrak sehingga foldernya berada langsung di akar proyek (`outputs/53-recordings/run.json`); jalankan `python scripts/demo_readiness.py` sebelum membuka dashboard. ZIP `outputs` tidak berisi cache data mentah untuk menjalankan ulang pipeline.

**IoT Patient Monitoring & Big Data Analytics · Iteration 03**

VitalFlow answers a monitoring question: **how do the levels and completeness of HR, pulse, respiration, and SpO₂ vary over a recording?** It builds a reproducible local Spark pipeline for the Itenas IFB-451 midterm. It integrates official BIDMC numerics with recording metadata, audits quality, writes and reads back Parquet, and produces evidence for all five Vs.

**Historical hospital monitor data · Simulated batch arrivals · Educational analysis.** This prototype has no connection to live devices and makes no clinical predictions or recommendations.

## ETS submission package

Use the [final readiness report](docs/FINAL_READINESS_REPORT.md) and [rubric audit](docs/final-rubric-audit.md) to verify the release. For the five-person video, start with the [narration](docs/presentation/video-script.md) and [storyboard](docs/presentation/storyboard.md), then follow the [recording guide](docs/presentation/recording-guide.md), [speaker notes](docs/presentation/speaker-notes.md), [caption transcript](docs/presentation/subtitle-transcript.md), and [video checklist](docs/presentation/video-checklist.md).

```sh
.venv/bin/python -m pip install -e '.[dashboard,dev,submission]'
.venv/bin/python scripts/demo_readiness.py       # Validate persisted Complete evidence
.venv/bin/python scripts/generate_submission.py  # Three-page A4 draft and architecture.svg
```

The draft is generated under `docs/submission/generated/`. Fill the [group details template](docs/submission/submission-data.example.json) with the real group number, five names and NIMs, and the uploaded video URL. Follow the [submission template and verification instructions](docs/submission/submission-template.md) to generate and check five individually named PDFs. Only the students can verify access to their actual video and submit their own PDFs in Itenas eLearning.

## Preview

Screenshots use the verified **Complete · 53 rekaman** snapshot.

![VitalFlow Overview](docs/screenshots/overview.png)

| Recording Explorer | Big Data 5Vs Lab · Volume |
|:---:|:---:|
| ![Recording Explorer](docs/screenshots/recording-explorer.png) | ![Big Data 5Vs Lab · Volume](docs/screenshots/lab-volume.png) |
| **Velocity** | **Variety** |
| ![Big Data 5Vs Lab · Velocity](docs/screenshots/lab-velocity.png) | ![Big Data 5Vs Lab · Variety](docs/screenshots/lab-variety.png) |
| **Veracity** | **Value** |
| ![Big Data 5Vs Lab · Veracity](docs/screenshots/lab-veracity.png) | ![Big Data 5Vs Lab · Value](docs/screenshots/lab-value.png) |
| **System Architecture** | **Evidence & Methodology** |
| ![System Architecture](docs/screenshots/architecture.png) | ![Evidence & Methodology](docs/screenshots/evidence.png) |

## Launch the dashboard

From the VitalFlow directory with its Python 3.12 virtual environment:

```sh
source .venv/bin/activate
python -m pip install -e '.[dashboard,dev]'
python -m streamlit run dashboard/app.py --server.headless true --server.port 8512
```

Open [http://127.0.0.1:8512](http://127.0.0.1:8512). The default selection is Complete. Choose **Fast**, **Default**, or **Complete** in the sidebar to load the corresponding verified snapshot. If that snapshot is missing, the dashboard provides the commands to generate it. For example, after downloading the full dataset once, `vitalflow run --mode complete` rebuilds the evidence without internet access.

The dashboard uses local evidence and does not start Spark. Streamlit, Plotly, and pandas present the saved outputs. PyArrow reads the selected recording from Parquet; the other pages use precomputed evidence. The simulated replay animates archived arrival intervals and measurements. It does not rerun ingestion or modify benchmark files. Use the [recording guide](docs/presentation/recording-guide.md) and the [dashboard verification record](docs/dashboard-verification.md).

Run both dashboard and pipeline checks offline with:

```sh
python -m pytest -q --junitxml=outputs/dashboard-qa/pytest.xml
ruff check .
ruff format --check .
```

## Start here

Use CPython 3.12 and a supported JDK. The tested stack on Apple Silicon was **Python 3.12.14, Temurin 25.0.4.1, PySpark 4.2.1, and pytest 8.4.2**. Spark runs with two local worker threads. See the [Spark 4.2.1 requirements](https://spark.apache.org/docs/4.2.1/) for supported JDKs; use the tested versions for the closest reproduction. If macOS has several JDKs, select Java 25 with `export JAVA_HOME="$(/usr/libexec/java_home -v 25)"`.

If Python 3.12 is missing on macOS, install it with [Homebrew](https://formulae.brew.sh/formula/python@3.12): `brew install python@3.12`. If you need a JDK, get the macOS ARM64 JDK from [Eclipse Adoptium](https://adoptium.net/temurin/releases/?version=25).

From the directory containing this README:

```sh
python3.12 --version
java -version
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pip check

vitalflow download --mode fast    # Internet; six data files and official checksums
vitalflow run --mode fast         # Offline; outputs/03-recordings/
python -m pytest -q               # Offline; uses isolated synthetic fixtures
```

The editable install keeps the CLI and its generated paths anchored to this checkout, even when called from another working directory. The script wrappers `python scripts/download_data.py` and `python scripts/run_pipeline.py` accept the same options as their respective subcommands. Python 3.9 shipped with some versions of macOS does not meet the project requirement.

| Selection | Recordings | Output |
| --- | ---: | --- |
| `--mode fast` | 3 | `outputs/03-recordings/` |
| `--mode default` or no flag | 10 | `outputs/10-recordings/` |
| `--mode complete` | 53 | `outputs/53-recordings/` |
| `--recordings N` | First N, 1–53 | `outputs/NN-recordings/` |

For the full evidence set, run `vitalflow download --mode complete`, then `vitalflow run --mode complete`. Once downloaded, repeat either `vitalflow download --mode complete --offline` to verify the cache or `vitalflow run --mode complete` to regenerate the artifacts. `--replay-interval 0.5` changes the target wall-clock interval in seconds. The default is 1 second. Reports distinguish source elapsed time from replay wall-clock time.

## Read a run

Each recording count has its own generated snapshot. Open these files in order:

| Artifact | What it shows |
| --- | --- |
| `run.json` | Runtime, row accounting and execution summary |
| `provenance.json`, `source_schema.json` | Verified file URLs, checksums, exact headers and observed token types per recording |
| `data/metadata/recordings.jsonl`, `integration.json` | Derived JSON, join cardinality, typed schemas and example output |
| `quality/source.json`, `quality/time_coverage.csv` | Before/after source quality and sampling cadence by recording |
| `quality/controlled_fixture.json` | Separate stress test for duplicate and invalid inputs |
| `data/processed/observations.parquet/` | Verified integrated data |
| `analytics/by_recording.csv`, `analytics/by_minute.csv` | Spark SQL descriptive statistics, valid counts and completeness |
| `benchmarks/volume.json`, `benchmarks/*_plan.txt` | Materialized timings and plans for group/count vs. join plus time grouping |
| `benchmarks/velocity.json`, `benchmarks/velocity_batches.csv` | Measured local arrivals, processing, queue waits, and counts |

The complete selection is the best evidence for Veracity: the original data contain missing readings and one negative elapsed timestamp. The fast selection still exercises the same pipeline and includes the separate controlled quality report.

## Reproduce and troubleshoot

- A missing file in `run` or `download --offline` means the selected cache is incomplete. Run `vitalflow download` with the same selection while online. Verified files are reused; a partial failure preserves successfully validated files.
- A checksum mismatch stops execution. Move the named invalid file out of the cache and rerun `download`. VitalFlow never replaces a raw file. The PhysioNet checksums and cached bytes live under `data/raw/bidmc/1.0.0/`.
- For a Java gateway error, check `java -version` and `JAVA_HOME` before restarting. Spark may warn that native Hadoop libraries are unavailable on macOS; this run uses bundled Java libraries and local files. No Hadoop server, Kafka, cloud service, Docker, or API key is required.
- To keep notes or copy a run for submission, store them outside `outputs/NN-recordings/`. That directory is reserved for generated artifacts and is replaced on a successful rerun. Timing, run timestamps, Spark plan IDs, and Parquet part filenames can change; inputs and analytical contents should be stable.

See the [architecture](docs/architecture.md), [dataset and citations](docs/dataset.md), [methodology](docs/methodology.md), [evidence and team roles](docs/evidence-matrix.md), [engineering decisions](docs/decisions.md), and [Iteration 01 verification record](docs/verification.md).
