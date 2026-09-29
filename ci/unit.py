"""Run unit tests. Extra args pass through to pytest."""

import sys

from common import run


def cmd_test(args):
    print("Running tests...")
    run([sys.executable, "-m", "pytest", *args])
