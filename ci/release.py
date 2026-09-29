"""Lint, test, bump, build, publish, tag."""

from common import run
from lint import run_lint
from pkg import bump
from unit import cmd_test


def cmd_release(_args):
    run_lint("no-edit")
    cmd_test([])
    version = bump()
    print(f"Bumped version to {version}")
    run(["poetry", "build"])
    run(["poetry", "publish"])
    run(["git", "add", "pyproject.toml"])
    run(["git", "commit", "-m", f"Bump version to {version}"])
    run(["git", "tag", f"v{version}"])
    print(f"Successfully published version {version}")
