"""Check local demo evidence, or execute the presentation's SQL on persisted Parquet."""

import argparse
from pathlib import Path

from vitalflow.config import PROJECT_ROOT, Project
from vitalflow.dashboard.evidence import PARQUET, PLANS, EvidenceError, EvidenceRepository

SQL = """
SELECT recording_id, COUNT(*) AS rows,
       COUNT(resp) AS resp_valid, ROUND(AVG(resp), 4) AS resp_mean
FROM demo_observations
WHERE recording_id = 'bidmc_13'
GROUP BY recording_id
""".strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--query", action="store_true", help="Execute and verify a Spark SQL clip.")
    args = parser.parse_args()
    repo = EvidenceRepository(Project(args.root.resolve()))
    try:
        snapshot = repo.load("complete")
        root = repo.path("complete")
        rid = "bidmc_13"
        row = snapshot.recordings.set_index("recording_id").loc[rid]
        data = repo.recording(
            "complete", rid, int(row["rows"]), repo.revision("complete", detail=True)
        )
        if data["resp"].count() != row["resp_valid"]:
            raise ValueError("RESP Parquet tidak cocok dengan ekspor SQL.")
        for plan in PLANS.values():
            if "Physical Plan" not in (root / plan).read_text(encoding="utf-8"):
                raise ValueError(f"Physical plan tidak tersedia: {plan}")
        if args.query:
            from vitalflow.spark import session

            spark = session()
            try:
                spark.read.parquet((root / PARQUET).as_uri()).createOrReplaceTempView(
                    "demo_observations"
                )
                print(SQL, flush=True)
                result = spark.sql(SQL)
                observed = result.collect()
                if len(observed) != 1 or (
                    observed[0].rows,
                    observed[0].resp_valid,
                    observed[0].resp_mean,
                ) != (row["rows"], row["resp_valid"], row["resp_mean"]):
                    raise ValueError("Kueri demo tidak cocok dengan ekspor SQL.")
                result.show(truncate=False)
            finally:
                spark.stop()
        print(
            f"Complete siap: {snapshot.metrics.recordings} rekaman, "
            f"{snapshot.metrics.retained} baris tersimpan; snapshot {snapshot.run['completed_at_utc']}."
        )
    except (EvidenceError, OSError, ValueError) as exc:
        parser.exit(1, f"Demo belum siap: {exc}\n")


if __name__ == "__main__":
    main()
