"""
State management module for persisting application state to JSON files.

This module provides a simple key-value store backed by JSON files for
persisting application state across runs. It includes a StateFile class
for managing individual state files and a file() function for singleton
state file management.
"""

import json
import os
import pathlib
import threading
from typing import Any, Optional, TypeVar, Union

__all__ = ["state_file"]

T = TypeVar("T", bound=Any)  # Generic type for better return typing


class StateFile:
    """
    Manages a JSON-based state file for persisting key-value data.

    StateFile provides a dictionary-like interface to store and retrieve
    values in a JSON file. It supports automatic flushing to disk and
    maintains an in-memory cache for performance.

    Can be used as a context manager:
        with StateFile("path/to/file.json") as state:
            state.set("key", "value")
    """

    def __init__(self, file_path: str, auto_flush: bool = True) -> None:
        """
        Initialize a new StateFile.

        Args:
            file_path: Path to the JSON file where state will be stored
            auto_flush: If True, changes are immediately written to disk
        """
        self._path: str = file_path
        self._cache: Optional[dict[str, Any]] = None
        self._auto_flush: bool = auto_flush
        self._dirty: bool = False
        self._path_ensured: bool = False
        dir_name: str = os.path.dirname(file_path)
        if dir_name:
            pathlib.Path(dir_name).mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> "StateFile":
        """
        Enter the context manager.

        Returns:
            The StateFile instance itself
        """
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Exit the context manager.

        Ensures any pending changes are flushed to disk before exiting.

        Args:
            exc_type: The type of exception that was raised, if any
            exc_val: The exception instance that was raised, if any
            exc_tb: The traceback for the exception, if any
        """
        self.flush()

    def _data(self, reload: bool = False) -> dict[str, Any]:
        """
        Get the current state data, loading from disk if necessary.

        Args:
            reload: If True, force reloading from disk even if cached

        Returns:
            Dictionary containing the current state
        """
        if self._cache is None or reload:
            if os.path.exists(self._path):
                with open(self._path) as f:
                    self._cache = json.load(f)
            else:
                self._cache = {}
            self._dirty = False
        # Add explicit assertion to help type checker
        assert self._cache is not None
        return self._cache

    def flush(self) -> None:
        """
        Write any pending changes to disk.

        If there are no pending changes or no data has been loaded,
        this method does nothing.
        """
        if self._cache is None or not self._dirty:
            return

        # Ensure the directory exists before writing
        if not self._path_ensured:
            dir_name = os.path.dirname(self._path)
            if dir_name:
                pathlib.Path(dir_name).mkdir(parents=True, exist_ok=True)

        with open(self._path, "w") as f:
            json.dump(self._cache, f, indent=4)
        self._dirty = False

    def get(self, key: str, default: Optional[T] = None, reload: bool = False) -> Union[Any, Optional[T]]:
        """
        Get a value from the state file.

        Args:
            key: The key to look up
            default: Value to return if key is not found
            reload: If True, reload from disk before looking up

        Returns:
            The value associated with the key, or the default if not found
        """
        key = str(key)  # because we are storing settings in JSON encoding, number keys will be converted to string.
        return self._data(reload).get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a value in the state file.

        Args:
            key: The key to set
            value: The value to store

        If auto_flush is enabled, changes are immediately written to disk.
        """
        data = self._data()
        key = str(key)  # because we are storing settings in JSON encoding, number keys will be converted to string.
        existing = data.get(key)
        if existing == value:
            return
        data[key] = value
        self._dirty = True
        if self._auto_flush:
            self.flush()

    def clear(self) -> None:
        """
        Clear all data from the state file.

        If auto_flush is enabled, changes are immediately written to disk.
        """
        self._cache = {}
        self._dirty = True
        if self._auto_flush:
            self.flush()

    def unset(self, key: str, reload: bool = False) -> None:
        """
        Remove a key from the state file.

        Args:
            key: The key to remove
            reload: If True, reload from disk before removing

        If auto_flush is enabled, changes are immediately written to disk.
        If the key doesn't exist, this method does nothing.
        """
        key = str(key)  # because we are storing settings in JSON encoding, number keys will be converted to string.
        data = self._data(reload)
        if key not in data:
            return
        del data[key]
        self._dirty = True
        if self._auto_flush:
            self.flush()

    def delete(self) -> None:
        """
        Delete the state file from disk and clear the in-memory cache.
        """
        self.discard()
        if os.path.exists(self._path):
            os.remove(self._path)

    def discard(self) -> None:
        """
        Discard the state file from memory and clear the in-memory cache. But keep the file on disk.
        """
        self._cache = {}
        self._dirty = False
        with _lock:
            _file_map.pop(self._path, None)

    def __getattr__(self, name: str) -> Any:
        """
        Enable dot property access for reading values.

        This allows accessing state values using dot notation:
        state.propName instead of state.get("propName")

        Args:
            name: The property name to access

        Returns:
            The value associated with the property name, or None if not found
        """
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        return self.get(name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        self.set(name, value)

    def __str__(self) -> str:
        return str(self._data())


_file_map: dict[str, StateFile] = {}
_lock = threading.Lock()


def state_file(file_path: str) -> StateFile:
    file_path = os.path.abspath(os.path.expanduser(file_path))
    with _lock:
        if file_path in _file_map:
            return _file_map[file_path]
        state_file = StateFile(file_path)
        _file_map[file_path] = state_file
        return state_file
