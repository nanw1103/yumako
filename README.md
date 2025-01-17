# Yumako ![Yumako](doc/yumako.png) 

Vanilla python utilities.

[![PyPI version](https://badge.fury.io/py/yumako.svg)](https://badge.fury.io/py/yumako)
[![Python Versions](https://img.shields.io/pypi/pyversions/yumako.svg)](https://pypi.org/project/yumako/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)


Usage:
```python
import yumako
```

Yumako utilities are designed for human:
```python
print(yumako.time.of("2025-01-17"))
print(yumako.time.of("-3d"))
```

Yumako consists of extreme performant libraries:
```python
lru = yumako.lru.LRUDict(1000)
lru[1] = True
lru["hello"] = "ユマ果"
print(lru)
```
