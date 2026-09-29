#!/usr/bin/env python3
"""Dev commands. Wrapper: ./dev."""

import os
import sys
from pathlib import Path

from common import ROOT
from lint import cmd_lint, cmd_lint_no_edit
from pkg import cmd_build, cmd_bump, cmd_init, cmd_publish
from release import cmd_release
from unit import cmd_test


def ensure_poetry():
    if os.environ.get("POETRY_ACTIVE") == "1" or os.environ.get("YUMAKO_DEV_REEXEC") == "1":
        return
    os.environ["YUMAKO_DEV_REEXEC"] = "1"
    script = str(Path(__file__).resolve())
    os.execvpe("poetry", ["poetry", "run", "python", script, *sys.argv[1:]], os.environ)


def usage():
    print(
        """usage: ./dev <mode>

  init            poetry install
  lint            ruff format, ruff check, mypy, pylint
  lint-no-edit    same checks, write nothing
  test            pytest; extra args passed through
  build           poetry build
  bumpversion     bump pyproject.toml (patch, or minor, or major)
  publish         poetry publish
  release         lint-no-edit, test, bump, build, publish, tag
"""
    )


COMMANDS = {
    "init": cmd_init,
    "lint": cmd_lint,
    "lint-no-edit": cmd_lint_no_edit,
    "test": cmd_test,
    "build": cmd_build,
    "bumpversion": cmd_bump,
    "publish": cmd_publish,
    "release": cmd_release,
}


def main(argv):
    if sys.version_info < (3, 9):  # noqa: UP036
        print(f"ERROR: Python version is {sys.version_info[0]}.{sys.version_info[1]}, which is < 3.9", file=sys.stderr)
        sys.exit(101)
    cmd = argv[1] if len(argv) > 1 else ""
    rest = argv[2:]
    if cmd in ("", "-h", "--help", "help"):
        usage()
        sys.exit(0 if cmd else 2)
    if cmd not in COMMANDS:
        usage()
        sys.exit(2)
    os.chdir(ROOT)
    if cmd != "init":
        ensure_poetry()
    COMMANDS[cmd](rest)
    print("Done")


if __name__ == "__main__":
    main(sys.argv)
