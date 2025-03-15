import sys
from collections.abc import Iterator, Mapping
from typing import Any, Optional, Union, overload

__all__ = ["args"]


class _Args(Mapping[str, str]):
    """A case-insensitive, camel-snake-insensitive k-v argv accessor, for human.
    This means it's not a strict mapping, but more human-friendly.
    """

    def __init__(self) -> None:
        self._data: Optional[dict[str, str]] = None

    def _ensure_data(self) -> dict[str, str]:
        if self._data is None:
            self._data = {}
            previous_flag = None
            for arg in sys.argv[1:]:
                if "=" in arg:
                    key, value = arg.split("=", 1)
                else:
                    if previous_flag:
                        self._data[previous_flag] = arg
                        previous_flag = None
                        continue
                    else:
                        key = arg
                        value = "true"
                if key.startswith("--"):
                    key = key[2:]
                    previous_flag = key
                else:
                    previous_flag = None
                if key in self._data:
                    raise ValueError(f"Duplicate key: {key}")
                self._data[key] = value
        return self._data

    def __getitem__(self, k: str) -> str:
        v = self.get(k)
        if v is None:
            raise KeyError(f"Key not found: {k}")
        return v

    def __iter__(self) -> Iterator[str]:
        return iter(self._ensure_data())

    def __len__(self) -> "int":
        return len(self._ensure_data())

    def __str__(self) -> str:
        """Return a readable string representation of arguments."""
        return str(self._ensure_data())

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        cls_name = self.__class__.__name__
        return f"{cls_name}({self._ensure_data()})"

    def bool(self, k: str, default: bool = False) -> bool:
        v = self.get(k)
        if v is None:
            return default
        return v.lower() in ("true", "t", "yes", "y", "1", "on", "enabled")

    def int(self, k: str, default: int = 0) -> int:
        v = self.get(k)
        if v is None:
            return default
        return int(v)

    @overload
    def get(self, k: str) -> Optional[str]:
        ...

    @overload
    def get(self, k: str, default: Any) -> Union[str, Any]:
        ...

    def get(self, k: str, default: Optional[Any] = None) -> Union[str, Optional[Any]]:
        data = self._ensure_data()
        v = data.get(k)
        if v is not None:
            return v
        alt_k = k.replace("_", "").lower()
        for key in data:
            k2 = key.replace("_", "").lower()
            if alt_k == k2:
                return data[key]
        return default


args = _Args()
