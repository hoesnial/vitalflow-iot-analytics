# Dataset and attribution

**BIDMC PPG and Respiration Dataset v1.0.0.** Pimentel, M. A. F., Johnson, A., Charlton, P., & Clifton, D. (2018). PhysioNet. [Dataset and DOI 10.13026/C2208R](https://physionet.org/content/bidmc/1.0.0/). [Open Data Commons Attribution License v1.0](https://opendatacommons.org/licenses/by/1-0/). The dataset contains historical hospital recordings of approximately eight minutes each. PhysioNet documents 1 Hz numeric parameters and 125 Hz waveforms.

Cite the [original publication by Pimentel et al.](https://doi.org/10.1109/TBME.2016.2613124) and the platform citation requested by the [dataset page](https://physionet.org/content/bidmc/1.0.0/): Pollard et al. (2026), [PhysioNet as a global platform for biomedical research](https://doi.org/10.1038/s44360-026-00096-z), *Nature Health*. Put the full attribution in the video description.

## Source contract verified in the complete selection

- **53** `bidmc_XX_Numerics.csv` files and **53** `bidmc_XX_Fix.txt` files, **462,700 bytes** total (excluding the checksum manifest). Each numeric file has **481** data rows. The pipeline verifies each against PhysioNet's [SHA-256 list](https://physionet.org/files/bidmc/1.0.0/SHA256SUMS.txt). It does not fetch Signals, Breaths, WFDB, or MATLAB files.
- Every numeric CSV's exact header was `Time [s], HR, PULSE, RESP, SpO2` (a leading space on every field after the first). Each header and row shape is checked before Spark reads the file. Text values are inspected for integer, decimal/scientific, blank, NaN, or other tokens. All 53 actual files contain integer-formatted finite values and some channels also contain `NaN`. Spark first reads strings, then casts validated fields to doubles. Elapsed time is kept in seconds.
- HR and pulse are beats/min, RESP is breaths/min, and SpO₂ is percent. HR and pulse are distinct monitor measurements. Use the rates, completeness and relative time as recorded; the project does not infer blood pressure from the numeric files.
- The public `bidmc_XX` recording ID comes from the filename and must match the first marker in its corresponding Fix file. It is a **recording** key. VitalFlow makes no claim about uniqueness of individuals in the selected recordings.

## TXT to JSON

Parse only `Location`, `Numerics`, and the separate signals/numerics sampling frequency lines from each Fix file. Validate the numeric channel names and positive Hz values; store the channels as an array and the frequencies as numbers. Add the dataset version and official Fix URL for traceability. Spark uses an explicit schema to read the result as newline-delimited JSON and verifies exactly one metadata row per numeric recording.

The cache retains the upstream files unchanged. Derived metadata and reports omit age, gender, MIMIC subject identifiers, original recording identifiers, and upstream MIMIC paths. Use the derived metadata and aggregates for demonstrations. The labeled `data/scenarios/controlled_quality.csv` is hand-authored test input; it does not contain patient data and is excluded from the integrated Parquet, benchmarks and analytical summaries.
