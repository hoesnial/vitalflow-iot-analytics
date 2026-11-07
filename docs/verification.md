# Iteration 01 verification · 7 November 2026

Executed locally on macOS arm64 (16 GB) with CPython 3.12.14 and Temurin 25.0.4.1. The source directory and existing project files outside the new VitalFlow repository were left untouched.

- Created an isolated Python venv and ran `python -m pip install -e '.[dev]'` and `python -m pip check`. Core dependencies installed and checked. `python -m pip install --dry-run '.[dashboard]'` resolved the optional future dependencies without installing them.
- Ran the downloader against PhysioNet for all 53 pairs, including verification against the published SHA-256 manifest. One TLS handshake timed out and succeeded on retry. Downloaded 106 data files, totaling 462,700 bytes excluding the checksum list.
- Ran `vitalflow download --mode complete --offline`, `vitalflow run --mode fast`, `vitalflow run`, and `vitalflow run --mode complete`. Each run produced typed and audited source data, a guarded JSON join, Parquet readback and Spark SQL exports.
- Repeated the complete run offline. SHA-256 and modification times for all 107 cache files (including the checksum list) matched. Nine stable outputs, including both SQL exports and the quality reports, were byte-identical. Timings and timestamps were measured anew.
- Ran `python -m pytest -q`, `ruff check .`, and `ruff format --check .`. **16 tests passed.** Tests use a local controlled fixture and three mocked recording pairs, including a reordered header. The real PhysioNet CLI runs independently establish the official dataset results.

| Mode | Verified data files | Source rows | Metadata rows | Parquet readback rows | Replay batches |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fast | 6 | 1,443 | 3 | 1,443 | 5 |
| Default | 20 | 4,810 | 10 | 4,810 | 5 |
| Complete | 106 | 25,493 | 53 | 25,492 | 6 |

The complete run observed zero duplicate source time keys and zero gaps or short intervals among the retained timestamps relative to the reported 1 Hz numeric rate. One negative time was outside the analysis contract. The `NaN` counts retained as null were HR 4, pulse 128, RESP 153 and SpO₂ 128. Full run details are in the [evidence matrix](evidence-matrix.md) and generated snapshots.
