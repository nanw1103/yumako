import os
from collections.abc import Iterator, MutableMapping
from typing import Any, Union

__all__ = ["env"]


class _Env(MutableMapping[str, str]):
    """A case-insensitive environment variable accessor, for human."""

    def __getitem__(self, key: str) -> str:
        v = self.get(key)
        if v == "":
            raise KeyError(key)
        return v

    def __setitem__(self, key: str, value: str) -> None:
        key = key.upper()
        os.environ[key] = str(value)

    def __delitem__(self, key: str) -> None:
        key = key.upper()
        try:
            del os.environ[key]
        except KeyError:
            for k in os.environ.keys():
                if k.upper() == key:
                    del os.environ[k]
                    return

    def __iter__(self) -> Iterator[str]:
        return iter(os.environ)

    def __len__(self) -> "int":
        return len(os.environ)

    def __str__(self) -> str:
        """Return a readable string representation of arguments."""
        return str(dict(self))

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        cls_name = self.__class__.__name__
        return f"{cls_name}({dict(self)})"

    def get(self, key: str, default: Any = "") -> Union[str, Any]:
        key = key.upper()
        v = os.getenv(key)
        if v is not None:
            return v

        for k, v in os.environ.items():
            if k.upper() == key:
                return v
        return default

    def bool(self, key: str, default: bool = False) -> bool:
        v = self.get(key)
        if v == "":
            return default
        v = v.lower()
        return v in ["true", "t", "yes", "y", "1", "on", "enabled"]

    def int(self, key: str, default: int = 0) -> int:
        v = self.get(key)
        if v == "":
            return default
        return int(v)


env = _Env()
