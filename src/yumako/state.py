"""
State management module for persisting application state to JSON files.

This module provides a simple key-value store backed by JSON files for
persisting application state across runs. It includes both a StateFile class
for managing individual state files and convenience functions for working
with a default global state file.
"""

import json
import os
import pathlib
from typing import Any, Optional, TypeVar, Union, cast

T = TypeVar("T", bound=Any)  # Generic type for better return typing


class StateFile:
    """
    Manages a JSON-based state file for persisting key-value data.

    StateFile provides a dictionary-like interface to store and retrieve
    values in a JSON file. It supports automatic flushing to disk and
    maintains an in-memory cache for performance.
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
        self._cache = {}
        if os.path.exists(self._path):
            os.remove(self._path)
        self._dirty = False


# Module-level state for managing the default StateFile instance
_default: Optional[StateFile] = None


def init_default(file_path: str) -> StateFile:
    """
    Initialize the default StateFile with the given path.

    Args:
        file_path: Path to the JSON file for the default state

    Returns:
        The default StateFile instance

    Raises:
        ValueError: If the default StateFile was already initialized with a different path
    """
    global _default
    if _default is None:
        _default = StateFile(file_path)
    else:
        if _default._path != file_path:
            raise ValueError("StateFile already initialized with a different file path: " + _default._path)
    return _default


def default_state() -> StateFile:
    """
    Get the default StateFile instance.

    If not already initialized, creates a StateFile with the default path ".state".

    Returns:
        The default StateFile instance
    """
    global _default
    if _default is None:
        init_default(".state")
    return cast(StateFile, _default)  # We know it's not None after init_default
