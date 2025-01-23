#!/usr/bin/env -S python -W ignore

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str]) -> None:
    print(f"Running command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def lint() -> None:
    """Run linters."""
    run_command(["black", "."])
    run_command(["isort", "."])
    # run_command(["flake8", "src"])
    run_command(["mypy", "src"])
    run_command(["ruff", "check", ".", "--fix"])


def check() -> None:
    """Run all checks without modifying files."""
    run_command(["black", "--check", "."])
    run_command(["isort", "--check", "."])
    # run_command(["flake8", "src"])
    run_command(["mypy", "src"])
    run_command(["ruff", "check", "."])


def test() -> None:
    """Run tests."""
    run_command(["pytest"])


def bump_version(version_type: str = "patch") -> str:
    """Bump the version in pyproject.toml
    version_type can be 'major', 'minor', or 'patch'
    """

    import tomlkit

    pyproject_path = Path("pyproject.toml")

    with open(pyproject_path) as f:
        pyproject = tomlkit.parse(f.read())

    current_version = pyproject["project"]["version"]
    major, minor, patch = map(int, current_version.split("."))

    if version_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif version_type == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1

    new_version = f"{major}.{minor}.{patch}"
    pyproject["project"]["version"] = new_version

    with open(pyproject_path, "w") as f:
        f.write(tomlkit.dumps(pyproject))

    return new_version


def release() -> None:
    # Build and publish
    try:
        lint()
        test()

        # Bump version
        new_version = bump_version()
        print(f"Bumped version to {new_version}")

        run_command(["poetry", "build"])
        run_command(["poetry", "publish"])

        # Create and push git tag
        run_command(["git", "add", "pyproject.toml"])
        run_command(["git", "commit", "-m", f"Bump version to {new_version}"])
        run_command(["git", "tag", f"v{new_version}"])
        # run_command(["git", "push"])
        # run_command(["git", "push", "--tags"])

        print(f"Successfully published version {new_version}")
    except subprocess.CalledProcessError as e:
        print(f"Error during publish: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please specify operation: lint or release")
        sys.exit(1)

    operation = sys.argv[1]
    if operation == "lint":
        lint()
    elif operation == "release":
        release()
    else:
        print("Unknown operation. Supported operations: lint, release")
        sys.exit(1)
