# Yumako ![Yumako](doc/yumako.png) 

Vanilla python utilities.

[![PyPI version](https://badge.fury.io/py/yumako.svg)](https://badge.fury.io/py/yumako)
[![Python Versions](https://img.shields.io/pypi/pyversions/yumako.svg)](https://pypi.org/project/yumako/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)


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
print(yumako.time.of("2025-01-17H23:00:00.000-05:00"))  # Any popular timeformat
print(yumako.time.of("-3d"))  # 3 days ago

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
