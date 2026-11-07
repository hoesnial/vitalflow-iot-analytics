"""CLI: opt in to downloads; subsequent runs operate offline."""

import argparse
import json
import logging
import sys
from collections import Counter

from .acquisition import acquire
from .config import MAX_RECORDINGS, MODES, REPLAY_INTERVAL_SECONDS, Project, VitalFlowError


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    for command, help_text in (
        ("download", "Download or verify cached official data and its SHA-256 manifest."),
        ("run", "Run the Spark pipeline using only cached source data."),
    ):
        args = commands.add_parser(command, help=help_text)
        selection = args.add_mutually_exclusive_group()
        selection.add_argument(
            "--mode",
            choices=MODES,
            default="default",
            help="fast=3, default=10, complete=53 (default: default)",
        )
        selection.add_argument(
            "--recordings",
            type=int,
            choices=range(1, MAX_RECORDINGS + 1),
            metavar="1-53",
            help="Use the first N recordings.",
        )
        if command == "run":
            args.add_argument(
                "--replay-interval",
                type=float,
                default=REPLAY_INTERVAL_SECONDS,
                help="Target seconds between simulated arrivals (default: %(default)s).",
            )
        else:
            args.add_argument(
                "--offline", action="store_true", help="Verify cache without network."
            )
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    count = MODES[args.mode] if args.recordings is None else args.recordings
    project = Project()
    try:
        if args.command == "download":
            records, manifest = acquire(project, count, offline=args.offline)
            result = {
                "recordings": len(records),
                "files": dict(Counter(row["status"] for row in manifest["files"])),
                "source_bytes": sum(row["bytes"] for row in manifest["files"]),
                "cache": str(project.raw.relative_to(project.root)),
                "checksum_manifest": manifest["checksum_manifest"],
            }
        else:
            from .pipeline import RunOptions, run
            from .spark import session

            options = RunOptions(count, args.replay_interval)
            spark = session()
            try:
                result = run(spark, project, options)
            finally:
                spark.stop()
    except (VitalFlowError, OSError) as exc:
        logging.error("%s", exc)
        return 1
    json.dump(result, sys.stdout, indent=2, sort_keys=True, allow_nan=False)
    sys.stdout.write("\n")
    return 0
