"""
Yumako - Vanilla python utilities.
"""

import importlib
from types import ModuleType
from typing import TYPE_CHECKING

__submodules = [
    "template",
    "time",
    "lru",
]
__submodule_map = {name: f"yumako.{name}" for name in __submodules}

if TYPE_CHECKING:
    from . import lru  # type: ignore
    from . import template  # type: ignore
    from . import time  # type: ignore


def __getattr__(name: str) -> ModuleType:
    if name in __submodule_map:
        submodule = importlib.import_module(__submodule_map[name])
        globals()[name] = submodule
        return submodule
    raise AttributeError(f"Module {__name__!r} has no attribute {name!r}")


__all__ = __submodules


def __dir__() -> list[str]:
    return __all__
