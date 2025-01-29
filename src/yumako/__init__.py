"""
Yumako - Vanilla python utilities.
"""

__all__ = [
    "template",
    "time",
    "lru",
    "args",
    "env",
]

import importlib as __importlib
from types import ModuleType as __ModuleType
from typing import TYPE_CHECKING as __TYPE_CHECKING
from typing import Any as __Any
from typing import Union as __Union

if __TYPE_CHECKING:
    from . import lru  # type: ignore
    from . import template  # type: ignore
    from . import time  # type: ignore

from .args import args as args
from .env import env as env


def __getattr__(name: str) -> __Union[__ModuleType, __Any]:
    submodule = __importlib.import_module("yumako." + name)
    globals()[name] = submodule
    return submodule


def __dir__() -> list[str]:
    return __all__
