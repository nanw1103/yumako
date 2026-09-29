"""Shared paths and process helpers for ci/dev.py commands."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd, cwd=None):
    result = subprocess.run(cmd, cwd=cwd or ROOT)
    if result.returncode != 0:
        sys.exit(result.returncode)
