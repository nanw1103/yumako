"""
Yumako - Vanilla python utilities.
"""

__all__ = [
    "args",
    "env",
    "state_file",
    "cache",
    "lru",
    "template",
    "time",
]

import importlib as __importlib
from types import ModuleType as __ModuleType
from typing import TYPE_CHECKING as __TYPE_CHECKING
from typing import Any as __Any
from typing import Union as __Union

if __TYPE_CHECKING:
    # namespace grouped submodules
    from . import cache  # type: ignore
    from . import lru  # type: ignore
    from . import template  # type: ignore
    from . import time  # type: ignore
    from .args import args as args  # type: ignore
    from .env import env as env  # type: ignore
    from .state import state_file as state_file  # type: ignore


def __getattr__(name: str) -> __Union[__ModuleType, __Any]:
    if name == "args" or name == "env":
        submodule = __importlib.import_module("yumako." + name)
        obj = object.__getattribute__(submodule, name)
        globals()[name] = obj
        return obj
    if name == "state_file":
        submodule = __importlib.import_module("yumako.state")
        obj = object.__getattribute__(submodule, name)
        globals()[name] = obj
        return obj

    submodule = __importlib.import_module("yumako." + name)
    globals()[name] = submodule
    return submodule


def __dir__() -> list[str]:
    return __all__
