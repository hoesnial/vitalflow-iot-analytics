# Evidence and presentation map

Use the **complete selection** for the main walkthrough. It produces two independent original data-quality findings and all five evidence files. Use the fast selection for a short live execution. Artifact names below are relative to `outputs/53-recordings/`.

| V | What to demonstrate | Evidence |
| --- | --- | --- |
| Volume · 10% | 25,492 retained observations linked to 53 metadata records. Group/count produces 53 rows; the broadcast hash join and elapsed-minute grouping produces 476. In a measured local run, median action times were 16.7 ms and 20.9 ms respectively. Show the added join, exchanges and grouping in the plans. | `benchmarks/volume.json`, both physical plans, `source_schema.json` |
| Velocity · 10% | Six simulated arrivals processed all 25,493 source rows. Actual intervals were about 997–1,006 ms against the 1-second target; median arrival-to-completion was 229 ms. The last batch carried the one invalid time. | `benchmarks/velocity.json`, `benchmarks/velocity_batches.csv` |
| Variety · 10% | Show the CSV strings, the Fix-derived JSON fields (including numeric Hz and an array of channels), and a joined record. The verified many-to-one join kept the count at 25,492. | `provenance.json`, `source_schema.json`, `data/metadata/recordings.jsonl`, `integration.json` |
| Veracity · 10% | The source had 413 missing measurement cells on 285 rows. All remain null. The source also has a time value of −1 s in `bidmc_23`; the pipeline excludes it under the elapsed-time rule and preserves the raw file. No duplicate source keys were found. The separate synthetic fixture changes 8 rows to 3 after removing 2 invalid times and 3 duplicate-key rows. | `quality/source.json`, `quality/time_coverage.csv`, `quality/controlled_fixture.json` |
| Value · 15% | Compare actual window averages and valid counts for the four channels. Flag periods where a mean is based on fewer readings. | `analytics/by_recording.csv`, `analytics/by_minute.csv` |

Timings are from one local run on 7 November 2026. Each rerun measures its own values. The comparison shows added operations, not a scale threshold or performance guarantee.

## Example interpretation

In `bidmc_01`, compare the first complete minute (0–59 s) with the last complete minute (420–479 s):

| Measure | First minute mean | Last complete minute mean |
| --- | ---: | ---: |
| HR (beats/min) | 93.08 | 90.70 |
| Pulse (beats/min) | 93.32 | 90.03 |
| RESP (breaths/min) | 24.05 | 21.33 |
| SpO₂ (%) | 97.15 | 96.85 |

The means describe this recording only. In the 60–119 s window, pulse and SpO₂ each had just 51 of 60 readings, while HR and RESP had 60. In `bidmc_13`, RESP had 335 valid readings out of 481 (69.6%) while the other channels were complete. A monitor data reviewer could use such differences to prioritize which channel and time window to inspect before interpreting a trend. The data alone cannot explain why readings were missing or why the values changed.

## Five student handoffs

| Time | Role and module | Evidence to show |
| --- | --- | --- |
| 0:00–0:45 | Project lead / analyst · M1 | State the monitoring question, historical data scope, five Vs and original source. |
| 0:45–1:30 | System engineer · M2 | Follow the architecture from immutable cache to outputs; explain local batch processing and timed replay. |
| 1:30–2:30 | Data engineer · M3–M4 | Show typed CSV and JSON integration, Parquet and source audit. Explain where a distributed filesystem would fit and why local files are sufficient here. |
| 2:30–3:45 | Big Data developer · M5–M6 | Compare aggregation and broadcast join plans, describe partial aggregation/shuffle/final aggregation, and report measured arrivals separately from query performance. |
| 3:45–5:00 | Data analyst · M7 | Show SQL summaries, channel completeness and the interpretation limits. |

The assignment allocates the remaining rubric to technical implementation (25%), healthcare relevance (10%), and teamwork/presentation (10%). For the final submission due **10 November 2026**, prepare a YouTube video of at most five minutes with all five students and English or Bahasa Indonesia captions. Submit the three-page PDF individually in Itenas eLearning as `GroupNumber_FullName_NIM.pdf`: (1) project, team/NIM and dataset; (2) YouTube link and five-V evidence; (3) architecture diagram. These final deliverables and the dashboard are outside Iteration 01.
