import subprocess


def run_command(cmd: list[str]) -> None:
    print(f"Running command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def lint() -> None:
    """Run linters."""
    run_command(["black", "."])
    run_command(["isort", "."])
    run_command(["flake8", "src"])
    run_command(["mypy", "src"])
    run_command(["ruff", "check", "."])


def check() -> None:
    """Run all checks without modifying files."""
    run_command(["black", "--check", "."])
    run_command(["isort", "--check", "."])
    run_command(["flake8", "src"])
    run_command(["mypy", "src"])
    run_command(["ruff", "check", "."])


def test() -> None:
    """Run tests."""
    run_command(["pytest"])

