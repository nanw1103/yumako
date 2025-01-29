# Yumako ![Yumako](doc/yumako.png) 

Vanilla python utilities, for humans.

[![PyPI version](https://badge.fury.io/py/yumako.svg)](https://badge.fury.io/py/yumako)
[![Python Versions](https://img.shields.io/pypi/pyversions/yumako.svg)](https://pypi.org/project/yumako/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Typed](https://img.shields.io/badge/Typed-Yes-blue.svg)](https://github.com/yumako/yumako)
[![Downloads](https://static.pepy.tech/badge/yumako)](https://pepy.tech/projects/yumako)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Sourcery](https://img.shields.io/badge/Sourcery-enabled-brightgreen)](https://sourcery.ai)
[![pylint: errors-only](https://img.shields.io/badge/pylint-errors--only-brightgreen)](https://github.com/pylint-dev/pylint)


## What Yumako should include

- Human-friendly utilities.
- Utilities that are for generic use cases, not domain-specific.
- High performance utilities.
- Utilities based on vanilla python, no external dependencies. 


Install:
```bash
pip install yumako

# Yumako utilities are based on vanilla python: no other dependencies.
```

Usage:
```python
import yumako
# Yumako submodules are loaded only when needed.

# ---------------------------------------
# Yumako utilities are designed for human
# ---------------------------------------
print(yumako.time.of("2025-01-17H23:00:00.000-05:00"))  # most popular time formats
print(yumako.time.of("-3d"))  # most intuitive human-friendly formats

seconds = yumako.time.duration("3m4s")  # 3m4s -> 184 seconds
delta = timedelta(seconds=seconds)
print(yumako.time.display(delta))  # 3m4s

# ---------------------------------------
# Yumako utilities are highly performant
# ---------------------------------------
lru = yumako.lru.LRUDict()
lru[1] = True
lru["hello"] = "mortal"
print(lru)

lru_set = yumako.lru.LRUSet()
lru_set.add("ユマ果")
print(lru_set)
```
