"""Equivalent to vitalflow run; install the package first."""

import sys

from vitalflow.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["run", *sys.argv[1:]]))
