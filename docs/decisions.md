# Engineering decisions

| Decision | Rationale and trade-off |
| --- | --- |
| Spark 4.2.1, Python 3.12, Java 25.0.4.1 | Reuse the compatible JDK on the actual Mac. An isolated venv separates the project from system Python. Spark workers are explicitly pointed at the same interpreter. The Spark/Py4J pair and dev tools are pinned. |
| Spark Classic in local mode, local filesystem and Parquet | Enough to show columnar storage, planning, shuffles, joins and SQL on the Mac. Bundled Hadoop client libraries are present, but no HDFS, YARN, or Hadoop MapReduce jobs are run. |
| SHA-256 plus validation before publication | Reject errors masquerading as files, truncation and mismatched bytes. Validated files survive partial download failures. A corrupt cached file is reported and preserved for the user to move. |
| Strings first, typed DataFrames second | Preserve missing-token distinctions and avoid type inference masking malformed cells. Record actual headers by file; group equal layouts and map reordered columns explicitly. |
| Allowlisted metadata and broadcast lookup | The Fix files actually provide the derived attributes, and the lookup has at most 53 rows. Cardinality is verified before using it to enrich data. |
| Snapshot by recording count | Complete staging keeps results from normal failed runs out of the published directory. A local lock prevents concurrent writers for the same selection. A short directory swap replaces the prior generated result; this is not a transaction store for concurrent readers or abrupt power loss. |
| Separate historical replay and synthetic quality fixture | Replay measures actual local arrival and Spark processing without pretending to receive live data. The fixture covers edge cases without altering the source or polluting analytics. |
| Defer dashboard | Iteration 01 pins pandas, Streamlit, and Plotly in an optional extra for later dependency resolution. They are not required or imported by the data pipeline. |
