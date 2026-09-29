"""Dot-access dicts, plus JSON load and save.

``DotDict`` reads and writes keys as attributes. ``dotify`` converts nested dicts.
``load`` and ``save`` read and write one JSON file.

``lock`` is optional. Pass ``lock(file, for_read)`` to lock that call.
``file`` is the open text file, so the lock covers the read or write.
``for_read`` is true for ``load`` and false for ``save``.
The caller owns retries and backoff. Omit ``lock`` and the call does not lock.
"""

import copy
import json
import os
from typing import IO, Any, Callable, Optional

__all__ = ["DotDict", "LockFile", "dotify", "load", "parse", "plain", "save", "undot"]

_MAX_DEPTH = 1000

LockFile = Callable[[IO[str], bool], None]


class DotDict(dict[str, Any]):
    """Dict whose keys are also attributes. A missing attribute is None."""

    def __getattr__(self, name: str) -> Any:
        return dict.get(self, name)

    def __setattr__(self, name: str, value: Any) -> None:
        dict.__setitem__(self, name, value)

    def __delattr__(self, name: str) -> None:
        dict.__delitem__(self, name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, dict):
            return dict(self) == dict(other)
        return NotImplemented

    def __deepcopy__(self, memo: Optional[dict[int, Any]] = None) -> "DotDict":
        copied: dict[str, Any] = {}
        for key in self:
            copied[key] = copy.deepcopy(self[key], memo)
        return DotDict(copied)

    def __repr__(self) -> str:
        return dict.__repr__(self)


def _too_deep(depth: int) -> None:
    if depth > _MAX_DEPTH:
        raise RecursionError("maximum recursion depth exceeded")


def dotify(target: Any, _depth: int = 0) -> Any:
    """Return ``target`` with every dict replaced by a ``DotDict``."""
    _too_deep(_depth)
    if isinstance(target, list):
        return [dotify(item, _depth + 1) for item in target]
    if isinstance(target, dict):
        return DotDict({key: dotify(value, _depth + 1) for key, value in target.items()})
    return target


def undot(target: Any, _depth: int = 0) -> Any:
    """Return ``target`` with every dict replaced by a plain dict."""
    _too_deep(_depth)
    if isinstance(target, list):
        return [undot(item, _depth + 1) for item in target]
    if isinstance(target, dict):
        return {key: undot(value, _depth + 1) for key, value in target.items()}
    return target


def plain(target: Any, _depth: int = 0) -> Any:
    """Return JSON-ready values. Dicts become plain dicts. Other objects stay as they are."""
    _too_deep(_depth)
    if target is None or isinstance(target, (str, bool, int, float)):
        return target
    if isinstance(target, list):
        return [plain(item, _depth + 1) for item in target]
    if isinstance(target, dict):
        return {key: plain(value, _depth + 1) for key, value in target.items()}
    return target


def parse(text: str) -> Any:
    """Parse a JSON string and dotify the result."""
    if not isinstance(text, str):
        raise TypeError("input must be a string")
    try:
        return dotify(json.loads(text))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc


def load(path: str, default: Any = None, lock: Optional[LockFile] = None) -> Any:
    """Load JSON from ``path`` and dotify it. A missing file returns ``dotify(default)``.

    ``default=None`` means the file is required. ``lock`` runs on the open file before the read.
    """
    if not os.path.exists(path):
        if default is None:
            raise ValueError(f"file not found: {path}")
        return dotify(default)
    try:
        with open(path, encoding="utf-8") as handle:
            if lock is not None:
                lock(handle, True)
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {path}") from exc
    except OSError as exc:
        raise ValueError(f"failed to read {path}") from exc
    return dotify(data)


def save(data: Any, path: str, pretty: bool = True, lock: Optional[LockFile] = None) -> None:
    """Write ``data`` as JSON. Pretty output uses a 4-space indent.

    ``lock`` runs on the open file before the write.
    """
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as handle:
            if lock is not None:
                lock(handle, False)
            json.dump(data, handle, indent=4 if pretty else None, default=vars)
    except OSError as exc:
        raise ValueError(f"failed to write {path}") from exc
    except TypeError as exc:
        raise ValueError(f"value is not JSON: {path}") from exc
