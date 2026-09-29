"""Format and lint. Ruff is the formatter and the linter."""

import sys

from common import run

PATHS = ["src", "tests", "examples", "ci"]


def run_lint(mode):
    format_cmd = [sys.executable, "-m", "ruff", "format", *PATHS]
    check_cmd = [sys.executable, "-m", "ruff", "check", *PATHS]
    if mode == "no-edit":
        format_cmd.append("--check")
    else:
        check_cmd.append("--fix")
    print(f"ruff format ({mode})...")
    run(format_cmd)
    print(f"ruff check ({mode})...")
    run(check_cmd)
    print("mypy...")
    run([sys.executable, "-m", "mypy", "src"])
    print("pylint...")
    # src only: pylint resolves stdlib time to yumako.time in tests and examples
    run([sys.executable, "-m", "pylint", "--errors-only", "--disable=import-error", "src"])


def cmd_lint(_args):
    run_lint("fix")


def cmd_lint_no_edit(_args):
    run_lint("no-edit")
