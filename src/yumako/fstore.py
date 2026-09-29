"""Directory of named values, one file per key, or memory when no path is given."""

import importlib
import json
import logging
import os
import shutil
import threading
import weakref
from collections.abc import Iterator
from typing import Any, Optional

from .jsondot import DotDict, LockFile, dotify, plain

__all__ = ["FStore"]

logger = logging.getLogger(__name__)

_MISSING = object()
_UNLOADED = object()
_stores_lock = threading.Lock()
_stores: weakref.WeakValueDictionary = weakref.WeakValueDictionary()


def _validate_key(key: str) -> None:
    if not key or key in (".", "..") or "/" in key or "\\" in key:
        raise ValueError(f"invalid key: {key}")


def _resolve_format(key: str, format: str) -> str:
    if format in ("text", "plain", "txt"):
        return "text"
    if format in ("json", "json-compact"):
        return format
    if format in ("yaml", "yml"):
        return "yaml"
    if format != "auto":
        raise ValueError(f"unsupported store format: {format}")
    ext = os.path.splitext(key)[1]
    if ext == ".txt":
        return "text"
    if ext in (".yaml", ".yml"):
        return "yaml"
    return "json"


def _yaml_module() -> Any:
    try:
        return importlib.import_module("yaml")
    except ImportError as exc:
        raise ImportError("YAML support needs the PyYAML package") from exc


def _dump_yaml(data: Any) -> str:
    yaml = _yaml_module()
    try:
        text = yaml.safe_dump(data, sort_keys=False)
    except Exception as exc:
        raise ValueError("value is not YAML") from exc
    if not isinstance(text, str):
        raise ValueError("value is not YAML")
    return text


def _read_yaml(path: str, lock: Optional[LockFile]) -> Any:
    yaml = _yaml_module()
    try:
        return yaml.safe_load(_read_text(path, lock))
    except Exception as exc:
        raise ValueError(f"invalid YAML: {path}") from exc


def _read_text(path: str, lock: Optional[LockFile]) -> str:
    try:
        with open(path, encoding="utf-8") as handle:
            if lock is not None:
                lock(handle, True)
            return handle.read()
    except OSError as exc:
        raise ValueError(f"failed to read {path}") from exc


def _read_json(path: str, lock: Optional[LockFile]) -> Any:
    try:
        return json.loads(_read_text(path, lock))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {path}") from exc


def _write_text(path: str, text: str, lock: Optional[LockFile]) -> None:
    try:
        with open(path, "w", encoding="utf-8") as handle:
            if lock is not None:
                lock(handle, False)
            handle.write(text)
    except OSError as exc:
        raise ValueError(f"failed to write {path}") from exc


def _list_sub_dirs(directory: str, depth: int) -> list[str]:
    def walk(current: str, level: int) -> list[str]:
        if depth != -1 and level > depth:
            return []
        found: list[str] = []
        with os.scandir(current) as entries:
            for entry in entries:
                if not entry.is_dir():
                    continue
                found.append(os.path.relpath(entry.path, directory))
                found.extend(walk(entry.path, level + 1))
        return found

    return walk(directory, 0)


class _Doc(dict[str, Any]):
    def __init__(self, initial: dict[str, Any], store: "FStore", name: str) -> None:
        super().__init__(initial)
        self._store = store
        self._name = name

    def __enter__(self) -> "_Doc":
        return self

    def __exit__(
        self, exc_type: Optional[type[BaseException]], exc_value: Optional[BaseException], traceback: Any
    ) -> None:
        if exc_type is None:
            self._store.save(self._name, self)


class FStore:
    """One store.

    A key is one path segment. ``""``, ``"."``, ``".."``, and a slash or backslash raise ``ValueError``.
    ``FStore(path)`` for the same directory returns the same object, so those callers share one cache.
    A memory-only store is always a new object. Calls on one store are serialized in this process.
    The cached object ``get`` returns stays shared. Membership is one map.
    ``store[key]`` raises ``KeyError`` when the name is missing. ``in``, ``len``, and ``for`` use this map.
    A directory refresh drops names whose files are gone and marks new files unloaded.
    The last write to a file is the one on disk.

    ponytail: no cross-process file lock. Add one in the caller if concurrent writers matter.
    """

    def __init__(self, store_path: Optional[str] = None, create: bool = True, lock: Optional[LockFile] = None) -> None:
        """``store_path`` is the directory. Omit it and the store stays in memory.

        ``create`` true (the default) makes the directory on the first ``save``.
        ``create`` false raises when that directory is missing. A path that is a file raises.
        A second ``FStore`` for a directory already in use returns that store and keeps its ``create`` flag.

        ``lock`` runs on the open file before each read or write, same as ``jsondot.load``/``save``.
        Omit it and file operations are not locked.
        """
        if getattr(self, "_ready", False):
            return
        path = os.path.realpath(os.path.expanduser(store_path)) if store_path else None
        self._init_store(path, create, lock)

    def __new__(
        cls, store_path: Optional[str] = None, create: bool = True, lock: Optional[LockFile] = None
    ) -> "FStore":
        if not store_path:
            return object.__new__(cls)
        key = os.path.realpath(os.path.expanduser(store_path))
        with _stores_lock:
            found = _stores.get(key)
            if isinstance(found, FStore):
                return found
            obj = object.__new__(cls)
            obj._init_store(key, create, lock)
            _stores[key] = obj
            return obj

    def _init_store(self, path: Optional[str], create: bool, lock: Optional[LockFile]) -> None:
        self._path = path
        self._create = create
        self._file_lock = lock
        self._path_checked = False
        self._entries: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._ready = True

    def get(self, key: str, reload: bool = False, format: str = "auto", default: Any = None) -> Any:
        """Return the stored value. A missing key returns ``default`` and leaves the store unchanged.

        A stored JSON ``null`` returns ``None``. Dicts are ``DotDict``, including nested dicts. Text stays a string.
        Until ``reload`` is true, this returns the value this instance last stored or loaded.

        ``format`` ``auto`` reads ``key`` when that file exists, otherwise ``key.json`` for a key with no extension.
        ``text``, ``plain``, ``txt``, or a key ending in ``.txt``, reads raw text.
        ``yaml``, ``yml``, or a key ending in ``.yaml`` or ``.yml``, reads YAML.
        PyYAML is imported only for that read and raises ``ImportError`` when missing.
        Any other format raises ``ValueError``.
        """
        _validate_key(key)
        with self._lock:
            if self._path is None:
                if self._loaded(key):
                    return self._entries[key]
                return dotify(default) if default is not None else None
            if not reload and self._loaded(key):
                return self._entries[key]
            loaded = self._load(key, format)
            if loaded is _MISSING:
                self._entries.pop(key, None)
                return dotify(default) if default is not None else None
            self._entries[key] = loaded
            return loaded

    def exists(self, key: str) -> bool:
        """True when ``contains`` is true."""
        return self.contains(key)

    def get_path(self, key: str) -> Optional[str]:
        """File path for ``key``. A memory-only store returns ``None``."""
        _validate_key(key)
        if self._path is None:
            return None
        return os.path.join(self._path, key)

    def save(self, key: str, data: Any, format: str = "auto") -> Any:
        """Store a copy of ``data`` and return that copy.

        Later changes to the passed object leave the stored value unchanged.
        ``format`` ``auto`` writes JSON, including a string. ``None`` is stored as JSON ``null``.
        ``json-compact`` writes one line. Tuples are stored as lists.
        ``text``, ``plain``, ``txt``, or a key ending in ``.txt``, writes a raw string
        and raises ``ValueError`` when ``data`` is not a string.
        ``yaml``, ``yml``, or a key ending in ``.yaml`` or ``.yml``, writes YAML.
        PyYAML is imported only for that write and raises ``ImportError`` when missing.
        Any other format raises ``ValueError``.
        """
        _validate_key(key)
        with self._lock:
            kind = _resolve_format(key, format)
            if kind == "text":
                if not isinstance(data, str):
                    raise ValueError(f"text store expects a string: {key}")
                stored: Any = data
                payload = data
            elif kind == "yaml":
                stored = dotify(data)
                payload = _dump_yaml(plain(stored))
            else:
                stored = dotify(data)
                try:
                    payload = json.dumps(plain(stored), indent=None if kind == "json-compact" else 4)
                except TypeError as exc:
                    raise ValueError(f"value is not JSON: {key}") from exc

            if self._path is not None:
                self._ensure_dir()
                _write_text(os.path.join(self._path, key), payload, self._file_lock)
                logger.debug("Write %s", key)
            self._entries[key] = stored
            return stored

    def delete(self, key: str) -> None:
        """Remove ``key`` from memory and delete its file."""
        _validate_key(key)
        with self._lock:
            self._entries.pop(key, None)
            if self._path is None:
                return
            file_path = os.path.join(self._path, key)
            if os.path.isfile(file_path):
                os.remove(file_path)

    def keys(self) -> list[str]:
        """File names in the directory, or the in-memory keys when there is no path.

        A directory refresh drops names whose files are gone. New files stay unloaded until ``get``.
        A missing directory returns ``[]``.
        """
        with self._lock:
            return self._sync()

    def _unloaded_keys(self) -> list[str]:
        """Names in the membership map whose values are not loaded yet.

        A memory-only store returns ``[]``.
        """
        with self._lock:
            names = self._sync()
            return [name for name in names if self._entries[name] is _UNLOADED]

    def children(self, depth: int = 0) -> list[str]:
        """Child directory names.

        ``depth`` 0 is the immediate children, a larger depth includes nested ones, and ``-1`` includes every level.

        A memory-only store raises ``ValueError``. A missing directory returns ``[]``.
        """
        if self._path is None:
            raise ValueError("child stores need a directory")
        if depth < -1:
            raise ValueError(f"invalid depth: {depth}")
        with self._lock:
            if not os.path.isdir(self._path):
                return []
            if depth == 0:
                return [name for name in os.listdir(self._path) if os.path.isdir(os.path.join(self._path, name))]
            return _list_sub_dirs(self._path, depth)

    def child(self, name: str) -> "FStore":
        """Store at ``<path>/<name>``, using the same ``create`` flag and ``lock``.

        A memory-only store raises ``ValueError``.
        """
        _validate_key(name)
        if self._path is None:
            raise ValueError("child stores need a directory")
        return FStore(os.path.join(self._path, name), create=self._create, lock=self._file_lock)

    def values(self) -> list[Any]:
        """Stored values, in ``keys`` order. A list snapshot, like ``dict.values`` materialized."""
        with self._lock:
            return [self.get(key) for key in self.keys()]

    def items(self) -> list[tuple[str, Any]]:
        """``(key, value)`` pairs, in ``keys`` order. A list snapshot, like ``dict.items`` materialized."""
        with self._lock:
            return [(key, self.get(key)) for key in self.keys()]

    def clear(self) -> None:
        """Remove every key. The directory stays."""
        with self._lock:
            for key in self.keys():
                self.delete(key)

    def destroy(self) -> None:
        """Drop memory and delete the directory. The next ``save`` creates it again when ``create`` is true."""
        with self._lock:
            self._entries.clear()
            self._path_checked = False
            if self._path is not None and os.path.isdir(self._path):
                shutil.rmtree(self._path)

    def size(self) -> int:
        """Number of keys."""
        with self._lock:
            return len(self.keys())

    def contains(self, key: str) -> bool:
        """True when ``key`` is in the membership map."""
        _validate_key(key)
        with self._lock:
            self._sync()
            return key in self._entries

    def __getitem__(self, key: str) -> Any:
        """Value for ``key``. A missing name raises ``KeyError``. A stored JSON ``null`` is ``None``."""
        if not isinstance(key, str):
            raise TypeError(f"key must be a string: {key!r}")
        _validate_key(key)
        with self._lock:
            self._sync()
            if key not in self._entries:
                raise KeyError(key)
            value = self.get(key)
            if key not in self._entries:
                raise KeyError(key)
            return value

    def __setitem__(self, key: str, value: Any) -> None:
        """``save(key, value)`` with ``format`` ``auto``."""
        if not isinstance(key, str):
            raise TypeError(f"key must be a string: {key!r}")
        self.save(key, value)

    def __delitem__(self, key: str) -> None:
        """``delete(key)``. A missing name raises ``KeyError``."""
        if not isinstance(key, str):
            raise TypeError(f"key must be a string: {key!r}")
        _validate_key(key)
        with self._lock:
            self._sync()
            if key not in self._entries:
                raise KeyError(key)
            self.delete(key)

    def __contains__(self, key: object) -> bool:
        """True when ``contains`` is true. A non-string or invalid key is false."""
        if not isinstance(key, str):
            return False
        try:
            return self.contains(key)
        except ValueError:
            return False

    def __len__(self) -> int:
        """``size``."""
        return self.size()

    def __iter__(self) -> Iterator[str]:
        """Names from ``keys``."""
        return iter(self.keys())

    def _loaded(self, key: str) -> bool:
        return key in self._entries and self._entries[key] is not _UNLOADED

    def _sync(self) -> list[str]:
        if self._path is None:
            return list(self._entries)
        if not os.path.isdir(self._path):
            self._entries.clear()
            return []
        names = [name for name in os.listdir(self._path) if os.path.isfile(os.path.join(self._path, name))]
        refreshed: dict[str, Any] = {}
        for name in names:
            refreshed[name] = self._entries[name] if name in self._entries else _UNLOADED
        self._entries = refreshed
        return names

    def patch(self, key: str, data: dict[str, Any]) -> DotDict:
        """Merge ``data`` into the stored object and return the ``DotDict``.

        A missing key starts from ``{}``. A non-object raises ``ValueError``.
        """
        with self._lock:
            existing = self.get(key)
            if existing is None:
                merged: dict[str, Any] = {}
            elif isinstance(existing, dict):
                merged = dict(existing)
            else:
                raise ValueError(f"document is not an object: {key}")
            merged.update(data)
            saved = self.save(key, merged)
            if not isinstance(saved, DotDict):
                raise ValueError(f"document is not an object: {key}")
            return saved

    def doc(self, key: str) -> _Doc:
        """Dict for ``key``, starting from ``{}`` when the key is missing.

        The ``with`` block saves that dict on a clean exit and leaves the store unchanged when the block raises.
        A non-object raises ``ValueError``.
        """
        existing = self.get(key, default={})
        if not isinstance(existing, dict):
            raise ValueError(f"document is not an object: {key}")
        return _Doc(existing, self, key)

    def _load(self, key: str, format: str) -> Any:
        if self._path is None:
            return _MISSING
        kind = _resolve_format(key, format)
        path = os.path.join(self._path, key)
        if kind == "text":
            if not os.path.isfile(path):
                return _MISSING
            logger.debug("Read %s", key)
            return _read_text(path, self._file_lock)
        if kind == "yaml":
            if not os.path.isfile(path):
                return _MISSING
            logger.debug("Read %s", key)
            return dotify(_read_yaml(path, self._file_lock))
        if os.path.isfile(path):
            logger.debug("Read %s", key)
            return dotify(_read_json(path, self._file_lock))
        if format == "auto" and os.path.splitext(key)[1] == "":
            alt = path + ".json"
            if os.path.isfile(alt):
                logger.debug("Read %s", key)
                return dotify(_read_json(alt, self._file_lock))
        return _MISSING

    def _ensure_dir(self) -> None:
        if self._path is None or self._path_checked:
            return
        if os.path.exists(self._path):
            if not os.path.isdir(self._path):
                raise ValueError(f"store path is not a directory: {self._path}")
        elif self._create:
            os.makedirs(self._path, exist_ok=True)
        else:
            raise ValueError(f"store path does not exist: {self._path}")
        self._path_checked = True
