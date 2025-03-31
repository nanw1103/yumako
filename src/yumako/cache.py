import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, TypeVar, Union, cast

from .lru import LRUDict

logger = logging.getLogger(__name__)

T = TypeVar("T")


# Global cache storage for ram_cache
@dataclass
class _Holder:
    timestamp: datetime
    data: Any


_ram_cache_data: LRUDict[str, _Holder] = LRUDict(capacity=1000)


def _with_file_cache(fn_populate_data: Callable[[], T], file_name: str, ttl_seconds: int) -> T:
    try:
        if os.path.exists(file_name):
            file_modified = datetime.fromtimestamp(os.path.getmtime(file_name))
            delta_seconds = (datetime.now() - file_modified).total_seconds()
            if delta_seconds <= ttl_seconds:
                logger.debug(f"Using file cache: {file_name}")
                with open(file_name) as f:
                    data = json.load(f)
                    return cast(T, data)
    except Exception as e:
        logger.error(f"Error loading cache {file_name}: {str(e)}")

    data = fn_populate_data()

    try:
        if data is not None:
            logger.debug(f"Writing cache: {file_name}")
            dir_name = os.path.dirname(file_name)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(file_name, "w") as f:
                json.dump(data, f, indent=4)
        else:
            logger.debug(f"Empty data: {file_name}")
    except Exception as e:
        logger.error(f"Error saving cache {file_name}: {str(e)}")

    return cast(T, data)


def file_cache(
    file_name: str, ttl: Union[str, int] = "1d", with_ram_cache: bool = True
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that caches function results in a JSON file.

    Args:
        file_name: Path to the cache file
        ttl: Time-to-live, either as integer for seconds, or a human-readable string in the
             format of yumako.time.duration, for example "1d" for 1 day, "20m" for 20 minutes,
             "1h" for 1 hour, etc.

    Returns:
        A decorator function that implements the caching behavior

    Example:
        @file_cache('data.json', ttl="1d")
        def fetch_data():
            return {'key': 'value'}
    """

    if isinstance(ttl, str):
        from yumako import time

        ttl_seconds = time.duration(ttl)
    else:
        ttl_seconds = ttl

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            def populate_data() -> T:
                return func(*args, **kwargs)

            if with_ram_cache:

                def populate_2() -> T:
                    return _with_file_cache(populate_data, file_name, ttl_seconds)

                return _with_ram_cache(populate_2, file_name, ttl_seconds)
            else:
                return _with_file_cache(populate_data, file_name, ttl_seconds)

        return wrapper

    return decorator


def _with_ram_cache(fn_populate_data: Callable[[], T], cache_key: str, ttl_seconds: int) -> T:
    holder = _ram_cache_data.get(cache_key)
    if holder is not None:
        delta_seconds = (datetime.now() - holder.timestamp).total_seconds()
        if delta_seconds <= ttl_seconds:
            return cast(T, holder.data)

    data = fn_populate_data()
    if data is not None:
        _ram_cache_data[cache_key] = _Holder(datetime.now(), data)
    return data


def ram_cache(ttl: Union[str, int] = "1d") -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that caches function results in RAM.

    Args:
        ttl: Time-to-live, either as integer for seconds, or a human-readable string in the
            format of yumako.time.duration, for example "1d" for 1 day, "20m" for 20 minutes,
            "1h" for 1 hour, etc.

    Returns:
        A decorator function that implements the RAM caching behavior

    Example:
        @ram_cache(ttl="1h")
        def fetch_data():
            return {'key': 'value'}
    """

    if isinstance(ttl, str):
        from yumako import time

        ttl_seconds = time.duration(ttl)
    else:
        ttl_seconds = ttl

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Create a unique cache key based on the function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            def populate_data() -> T:
                return func(*args, **kwargs)

            return _with_ram_cache(populate_data, cache_key, ttl_seconds)

        return wrapper

    return decorator
