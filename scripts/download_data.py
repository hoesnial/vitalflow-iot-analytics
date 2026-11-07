"""Equivalent to vitalflow download; install the package first."""

import sys

from vitalflow.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["download", *sys.argv[1:]]))
