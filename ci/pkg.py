"""Install, version bump, build, and publish."""

import sys

from common import ROOT, run


def next_version(current, version_type="patch"):
    major, minor, patch = map(int, current.split("."))
    if version_type == "major":
        return f"{major + 1}.0.0"
    if version_type == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def bump(version_type="patch"):
    import tomlkit

    path = ROOT / "pyproject.toml"
    doc = tomlkit.parse(path.read_text())
    new_version = next_version(doc["project"]["version"], version_type)
    doc["project"]["version"] = new_version
    path.write_text(tomlkit.dumps(doc))
    return new_version


def cmd_init(_args):
    run(["poetry", "install"])


def cmd_build(_args):
    run(["poetry", "build"])


def cmd_bump(args):
    kind = args[0] if args else "patch"
    if kind not in ("major", "minor", "patch"):
        sys.exit("version type must be major, minor, or patch")
    print(bump(kind))


def cmd_publish(_args):
    run(["poetry", "publish"])


if __name__ == "__main__":
    assert next_version("0.1.40") == "0.1.41"
    assert next_version("0.1.40", "minor") == "0.2.0"
    assert next_version("0.1.40", "major") == "1.0.0"
