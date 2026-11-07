# Methodology

**Question.** Over a historical BIDMC recording, how do the levels and availability of HR, pulse, RESP and SpO₂ vary? For a monitoring workflow, availability matters because a trend computed from only a few readings can look more informative than it is.

## Veracity and integration

1. Preserve exact headers and text-token counts per file. Reject malformed file structure and incorrect digests before a file enters the cache.
2. Classify each time or measurement cell as valid, blank, NaN, malformed, nonfinite, or out of range. Strip surrounding whitespace and accept decimal/scientific notation. Normalize signed zero to zero. Time and rate values must be finite and nonnegative; SpO₂ must also be at most 100%. These are broad format/domain checks. A zero RESP is retained because the source alone cannot establish whether it indicates physiology or monitor behavior.
3. Blank and NaN values count as source missingness. Malformed, nonfinite and out-of-range measurement cells become null and are counted separately. Keep the row when its time is usable. For the elapsed-time contract, exclude rows without a finite, nonnegative time. Preserve evidence by recording ID and retain the raw row in the immutable cache. Do not shift the time origin or impute measurements.
4. For repeated valid `(recording_id, time_s)` keys, keep the row with most valid readings. Break ties by ascending HR, pulse, RESP, SpO₂ with nulls last. This is a deterministic resolution for this prototype; it does not identify the clinically correct observation. If the normalized payloads tie, the output values are identical. No measurements are merged across candidate rows.
5. Compare exact source duplicate rows, repeated keys, conflicting normalized payloads and field status counts. The source report accounts for each removed row. Inspect short and long time steps in the cleaned, joined dataset against each recording's reported numeric cadence. The controlled scenario independently checks cases absent from the source.
6. Reject missing, unexpected, duplicate or unmatched metadata keys. The guarded join must preserve the count of cleaned numeric observations. Write Parquet, reload it, and verify schema types and row count before running SQL.

## Volume

Compare **A**, group observations by recording and count, with **B**, broadcast-join recording metadata, derive a 60-second elapsed-time bin, group by recording/location/bin and count. Both start with the same cached cleaned observations. Warm each action once, alternate the order across three measured trials, and materialize each result. The export includes individual timings, medians, row/group counts, shuffle settings, and the physical plans.

B performs a join and groups by a finer key, producing more groups. Spark may rewrite or coalesce stages. Use the plan to explain the actual work. Local timings include task scheduling and collection of the small result, fluctuate with the machine, and do not establish cluster scalability. The full numeric input is small; no duplicated-record scaling experiment is used.

## Velocity

Stage historical numeric rows in aligned 120-second recording-relative windows. These windows align time since each recording began; they do not imply contemporaneous patients. An invalid time has a separate unbucketed batch. An independent local producer moves each staged CSV into an inbox at a fixed target cadence; the consumer then reads the delivered CSV, runs the shared validation expressions, and materializes counts in Spark.

Record UTC wall-clock arrival, start, and completion timestamps. A monotonic clock measures actual arrival gaps, delay from the delivery schedule, queue wait, Spark CSV ingest plus processing, and arrival-to-completion latency. Replay accounting includes invalid time rows and must agree with the source audit. The last valid bucket can be smaller because it contains the 480-second endpoint. Timing excludes preparation of staged files and represents local replay, not device, network, or clinical response latency.

## Value

SQL groups reloaded Parquet by recording and by 60-second elapsed-time bin. Averages and ranges ignore null values. Completeness is valid cells divided by **retained rows in that group**, not an estimate of device uptime. A last bin can have a single reading; check `rows` and each channel's `*_valid` before interpreting a trend. The results describe short historical snapshots and cannot identify causes or diagnose conditions.
