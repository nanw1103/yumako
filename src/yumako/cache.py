import json
import logging
import os
import shutil
import threading
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional, TypeVar, Union, cast

from . import time
from .lru import LRUDict

__all__ = ["file_cache", "ram_cache", "FileCollection"]

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


class FileCollection:
    """
    Efficient persistent cache layer for remote collections with TTL management and optional RAM acceleration.

    FileCollection provides a thread-safe caching solution for collections fetched from remote sources
    (APIs, databases, etc.). It automatically manages cache expiration at two levels: collection-wide
    (list TTL) and per-item (item TTL), and optionally accelerates access with an in-RAM LRU cache.

    Key features:
    - Dual-level TTL management: separate expiration policies for collection lists and individual items
    - Optional in-RAM LRU cache for high-frequency access patterns
    - Thread-safe operations with per-path locking to minimize contention
    - Automatic resource pooling across multiple instances sharing the same base path
    - Standard Python collection interface (__iter__, __getitem__, __contains__, __len__)
    - Dict-like methods (keys(), values(), items()) for familiar API

    Example:
        collection = FileCollection(
            base_path="/cache/orders",
            list_fn=lambda: api.get_orders(),
            get_fn=lambda id: api.get_order(id),
            ttl_list="1h",           # Refresh list every hour
            ttl_item="1d",           # Keep items for 1 day
            lru_capacity=500         # Accelerate with 500-item RAM cache
        )

        # Access like a normal collection
        all_orders = collection.all()
        order = collection.get("ORDER123")
        if "ORDER456" in collection:
            print(collection["ORDER456"])
    """

    # Class-level shared resources keyed by normalized base_path
    _cache_locks: dict[str, threading.Lock] = {}  # One lock per base_path
    _shared_lru_caches: dict[str, LRUDict[str, Any]] = {}  # One cache per base_path
    _cache_ref_counts: dict[str, int] = {}  # Reference count per base_path
    # Global lock only for accessing the dicts above
    _global_lock = threading.Lock()

    def __init__(
        self,
        base_path: str,
        list_fn: Callable[[], list[Any]],
        get_fn: Callable[[str], Any],
        ttl_list: str = "1d",
        ttl_item: str = "1d",
        lru_capacity: int = 1000,
        id_extractor: Optional[Callable[[Any], str]] = None,
        id_field_name: Optional[str] = None,
    ) -> None:
        """
        Initialize the FileCollection.

        Args:
            base_path: Directory path where collection items will be stored
            list_fn: Callable that performs the real listing and returns a list of JSON objects
            get_fn: Callable that performs the real fetch given item_id and returns the item_data
            ttl_list: Time-to-live for the collection list cache (e.g., "1d", "1h", "30m")
            ttl_item: Time-to-live for individual item caches (e.g., "1d", "1h", "30m")
            lru_capacity: Capacity for in-RAM LRU cache. Defaults to 1000. Set to 0 to disable.
            id_extractor: Optional callable to extract ID from each object. If None,
                defaults to extracting the "id" field.
            id_field_name: Optional field name to extract ID from each object. Cannot be used
                together with id_extractor.

        Raises:
            ValueError: If base_path is the root directory, if ttl_item < ttl_list,
                or if both id_extractor and id_field_name are specified
        """
        # Normalize path and check if it's root
        self.base_path = os.path.normpath(os.path.abspath(base_path))
        normalized_path = self.base_path
        if normalized_path == os.path.sep:
            raise ValueError("base_path cannot be the root directory")

        # Validate and convert TTLs: item TTL must be >= list TTL
        ttl_list_seconds = time.duration(ttl_list)
        ttl_item_seconds = time.duration(ttl_item)
        if ttl_item_seconds < ttl_list_seconds:
            raise ValueError(
                f"ttl_item must be >= ttl_list (got ttl_item={ttl_item_seconds}s, ttl_list={ttl_list_seconds}s)"
            )

        # Store TTL values in seconds for internal use
        self._ttl_list_s = ttl_list_seconds
        self._ttl_item_s = ttl_item_seconds
        self.meta_file = os.path.join(self.base_path, ".meta")

        # Track normalized path for cache/lock operations
        self._normalized_base_path = self.base_path
        self._uses_shared_cache = False

        # Get or create per-base-path lock
        with FileCollection._global_lock:
            if self._normalized_base_path not in FileCollection._cache_locks:
                FileCollection._cache_locks[self._normalized_base_path] = threading.Lock()
        self._cache_lock = FileCollection._cache_locks[self._normalized_base_path]

        # Set up ID extractor
        if id_extractor is not None and id_field_name is not None:
            raise ValueError("Cannot specify both id_extractor and id_field_name")

        if id_field_name is not None:
            # Create extractor from field name
            self.id_extractor = lambda obj: str(
                obj.get(id_field_name) if isinstance(obj, dict) else getattr(obj, id_field_name)
            )
        elif id_extractor is None:
            # Default: extract from "id" field
            self.id_extractor = lambda obj: str(obj.get("id") if isinstance(obj, dict) else obj.id)
        else:
            self.id_extractor = id_extractor

        # Initialize LRU cache if capacity is specified
        # Multiple instances with same base_path share the same LRU cache
        self.lru: Optional[LRUDict[str, Any]] = None
        if lru_capacity > 0:
            if not isinstance(lru_capacity, int):
                raise ValueError("lru_capacity must be a positive integer or 0 to disable")

            # Use shared cache pool (per-base-path)
            with self._cache_lock:
                if self._normalized_base_path not in FileCollection._shared_lru_caches:
                    FileCollection._shared_lru_caches[self._normalized_base_path] = LRUDict(capacity=lru_capacity)
                    FileCollection._cache_ref_counts[self._normalized_base_path] = 0

                self.lru = FileCollection._shared_lru_caches[self._normalized_base_path]
                FileCollection._cache_ref_counts[self._normalized_base_path] += 1
                self._uses_shared_cache = True
        elif lru_capacity < 0:
            raise ValueError("lru_capacity must be a positive integer or 0 to disable")

        # Store the callable functions
        self.list_fn = list_fn
        self.get_fn = get_fn

        # Ensure directory exists
        os.makedirs(self.base_path, exist_ok=True)

    @staticmethod
    def _sanitize_item_id(item_id: str) -> str:
        r"""Sanitize item_id by replacing problematic filesystem characters with underscores.

        Replaces the following characters: / \ : * ? " < > | and null byte

        Args:
            item_id: The item ID to sanitize

        Returns:
            Sanitized item ID safe for use as filename
        """
        problematic_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|", "\x00"]
        sanitized = item_id
        for char in problematic_chars:
            sanitized = sanitized.replace(char, "_")
        return sanitized

    @staticmethod
    def _is_expired(elapsed_time_s: Optional[float], ttl_s: float) -> bool:
        """Check if elapsed time has exceeded TTL.

        Args:
            elapsed_time_s: Time elapsed since cache was stored, in seconds
            ttl_s: Time-to-live in seconds

        Returns:
            True if elapsed time exceeds TTL, False otherwise
        """
        if elapsed_time_s is None:
            return True
        return elapsed_time_s > ttl_s

    def __del__(self) -> None:
        """Cleanup: decrement reference count and remove cache if no more instances."""
        if self._uses_shared_cache:
            with self._cache_lock:
                if self._normalized_base_path in FileCollection._cache_ref_counts:
                    FileCollection._cache_ref_counts[self._normalized_base_path] -= 1
                    # Remove cache if no more instances using it
                    if FileCollection._cache_ref_counts[self._normalized_base_path] <= 0:
                        if self._normalized_base_path in FileCollection._shared_lru_caches:
                            FileCollection._shared_lru_caches[self._normalized_base_path].clear()
                            del FileCollection._shared_lru_caches[self._normalized_base_path]
                        del FileCollection._cache_ref_counts[self._normalized_base_path]

    def _get_meta(self) -> dict[str, Any]:
        """Load metadata from .meta file."""
        if not os.path.exists(self.meta_file):
            return {"list_time": None, "items": {}, "id_map": {}}
        try:
            with open(self.meta_file) as f:
                meta = cast(dict[str, Any], json.load(f))
                # Ensure id_map exists in loaded metadata
                if "id_map" not in meta:
                    meta["id_map"] = {}
                return meta
        except (OSError, json.JSONDecodeError):
            return {"list_time": None, "items": {}, "id_map": {}}

    def _save_meta(self, meta: dict[str, Any]) -> None:
        """Save metadata to .meta file."""
        with open(self.meta_file, "w") as f:
            json.dump(meta, f, indent=4)

    def _get_item_file_path(self, item_id: str, meta: Optional[dict[str, Any]] = None) -> str:
        """Get the file path for a specific item using id_map if available."""
        # If meta is provided, use id_map to get the sanitized ID
        if meta is not None and "id_map" in meta and item_id in meta["id_map"]:
            sanitized_id = meta["id_map"][item_id]
        else:
            # Otherwise, sanitize the ID on the fly
            sanitized_id = FileCollection._sanitize_item_id(item_id)
        return os.path.join(self.base_path, f"{sanitized_id}.json")

    def _load_item_from_file(self, item_id: str, meta: Optional[dict[str, Any]] = None) -> Any:
        """Load an item from its file, checking LRU cache first."""
        # Check LRU cache first
        if self.lru is not None:
            try:
                return self.lru[item_id]
            except KeyError:
                pass

        # Get file path using meta if available for efficient id_map lookup
        file_path = self._get_item_file_path(item_id, meta)
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path) as f:
                item_data = json.load(f)
                # Store in LRU cache
                if self.lru is not None:
                    self.lru[item_id] = item_data
                return item_data
        except (OSError, json.JSONDecodeError):
            return None

    def _save_item_to_file(self, item_id: str, item_data: Any, meta: Optional[dict[str, Any]] = None) -> None:
        """Save an item to its file, update id_map if needed, and update LRU cache."""
        sanitized_id = FileCollection._sanitize_item_id(item_id)

        # Update id_map if sanitized ID differs from original ID
        if meta is not None and sanitized_id != item_id:
            meta["id_map"][item_id] = sanitized_id

        file_path = os.path.join(self.base_path, f"{sanitized_id}.json")
        with open(file_path, "w") as f:
            json.dump(item_data, f, indent=4)
        # Also store in LRU cache
        if self.lru is not None:
            self.lru[item_id] = item_data

    def _get_all_items_from_disk(self, meta: Optional[dict[str, Any]] = None) -> list[Any]:
        """Load all items from disk using metadata as source of truth for item IDs.

        Iterates metadata keys instead of directory scan for efficiency.
        """
        items: list[Any] = []
        if meta is None:
            return items

        # Use metadata item IDs as source of truth (no directory scan needed)
        for item_id in meta.get("items", {}).keys():
            item_data = self._load_item_from_file(item_id, meta)
            if item_data is not None:
                items.append(item_data)
        return items

    def _remove_excessive_items(self, valid_item_ids: set[str], meta: Optional[dict[str, Any]] = None) -> None:
        """Remove files for items not in the valid set and clean up id_map."""
        try:
            for filename in os.listdir(self.base_path):
                if filename.endswith(".json") and filename != ".meta":
                    sanitized_id = filename[:-5]
                    # Find original ID from id_map or assume it's the same
                    if meta is not None and "id_map" in meta:
                        original_id = None
                        for orig_id, san_id in meta["id_map"].items():
                            if san_id == sanitized_id:
                                original_id = orig_id
                                break
                        if original_id is None:
                            original_id = sanitized_id
                    else:
                        original_id = sanitized_id

                    if original_id not in valid_item_ids:
                        file_path = os.path.join(self.base_path, filename)
                        try:
                            os.unlink(file_path)
                            # Clean up id_map entry
                            if meta is not None and "id_map" in meta and original_id in meta["id_map"]:
                                del meta["id_map"][original_id]
                        except OSError:
                            pass
        except OSError:
            pass

    def _ensure_list_fresh(self, refresh: bool = False) -> tuple[dict[str, Any], Optional[list[Any]]]:
        """Ensure list cache is fresh, performing refresh if TTL expired.

        Returns metadata and items list (None if cache was already fresh).
        Avoids redundant disk loads when just refreshed.

        Args:
            refresh: If True, bypass TTL and always fetch fresh data.

        Returns:
            Tuple of (metadata, items_list_or_none):
            - metadata: updated metadata dictionary
            - items_list_or_none: list of items if just refreshed, None if cache was fresh
        """
        current_time_s = datetime.now().timestamp()

        meta = self._get_meta()

        # Check if list cache is expired or if force refresh is requested
        if (
            not refresh
            and meta.get("list_time") is not None
            and not FileCollection._is_expired(current_time_s - meta["list_time"], self._ttl_list_s)
        ):
            # Cache is fresh, return metadata with None for items
            return meta, None

        # Cache expired, perform real listing
        items_list = self.list_fn()
        valid_item_ids = set()

        # Save each item and update metadata
        for item_obj in items_list:
            item_id = str(self.id_extractor(item_obj))
            valid_item_ids.add(item_id)
            self._save_item_to_file(item_id, item_obj, meta)
            meta["items"][item_id] = current_time_s

        # Remove items that are no longer in the collection
        self._remove_excessive_items(valid_item_ids, meta)

        # Update list refresh time
        meta["list_time"] = current_time_s
        self._save_meta(meta)

        # Return metadata with items list (just fetched)
        return meta, items_list

    def all(self, refresh: bool = False) -> list[Any]:
        """
        Get all items in the collection, using cache if not expired.

        Thread-safe (uses per-base-path lock).

        Args:
            refresh: If True, bypass cache and always fetch fresh data.

        Returns:
            List of items
        """
        with self._cache_lock:
            # Ensure list cache is fresh
            meta, items_list = self._ensure_list_fresh(refresh)

            # If just refreshed, return items directly (avoid redundant disk read)
            if items_list is not None:
                return items_list

            # Cache was fresh, load items from disk/LRU
            return self._get_all_items_from_disk(meta)

    def get(self, item_id: str, refresh: bool = False) -> Any:
        """
        Get a specific item, using cache if not expired.

        Honors both list TTL and item TTL:
        - If list TTL expired and item not in metadata, performs a single fetch
        - If item TTL expired, performs a single fetch

        Thread-safe (uses per-base-path lock).

        Args:
            item_id: The ID of the item to retrieve
            refresh: If True, bypass cache and always fetch fresh data.

        Returns:
            The item data, or None if not found
        """
        with self._cache_lock:
            current_time_s = datetime.now().timestamp()

            meta = self._get_meta()
            list_time = meta.get("list_time")
            item_time = meta.get("items", {}).get(item_id)

            # Check if item is in metadata and its cache is fresh
            if (
                not refresh
                and item_time is not None
                and not FileCollection._is_expired(current_time_s - item_time, self._ttl_item_s)
            ):
                # Item exists in metadata and item TTL is fresh
                return self._load_item_from_file(item_id, meta)

            # Item not in metadata or item TTL expired
            # Check if list TTL is also expired
            if (
                item_time is None
                and list_time is not None
                and not FileCollection._is_expired(current_time_s - list_time, self._ttl_list_s)
            ):
                # Item not in metadata but list is fresh - item doesn't exist
                return None

            # Either: item TTL expired, or list TTL expired and item not found
            # Perform single fetch
            item_data = self.get_fn(item_id)

            if item_data is not None:
                # Save item and update metadata
                self._save_item_to_file(item_id, item_data, meta)
                meta["items"][item_id] = current_time_s
                self._save_meta(meta)

            return item_data

    def clear(self) -> None:
        """Clear the entire collection by removing the folder and all its contents.

        Also removes from shared in-RAM LRU cache pool if this is the last instance.

        Thread-safe (uses per-base-path lock).
        """
        with self._cache_lock:
            # Clean up from shared cache pool
            if self._uses_shared_cache:
                if self._normalized_base_path in FileCollection._cache_ref_counts:
                    FileCollection._cache_ref_counts[self._normalized_base_path] -= 1
                    # Remove cache if no more instances using it
                    if FileCollection._cache_ref_counts[self._normalized_base_path] <= 0:
                        if self._normalized_base_path in FileCollection._shared_lru_caches:
                            FileCollection._shared_lru_caches[self._normalized_base_path].clear()
                            del FileCollection._shared_lru_caches[self._normalized_base_path]
                        del FileCollection._cache_ref_counts[self._normalized_base_path]
                self._uses_shared_cache = False

            # Remove the entire directory
            if os.path.exists(self.base_path):
                shutil.rmtree(self.base_path)

    def __iter__(self) -> Iterable[Any]:
        """
        Iterate over items in the collection.

        Returns:
            Iterator over items (not IDs)
        """
        return iter(self.all())

    def __getitem__(self, item_id: str) -> Any:
        """
        Get item by ID using subscript notation.

        Args:
            item_id: The ID of the item to retrieve

        Returns:
            The item data

        Raises:
            KeyError: If item is not found
        """
        item = self.get(item_id)
        if item is None:
            raise KeyError(item_id)
        return item

    def __contains__(self, item_id: str) -> bool:
        """
        Check if an item ID exists in the collection.

        Honors list TTL - will fetch fresh data if cache expired.

        Args:
            item_id: The ID to check

        Returns:
            True if the item exists, False otherwise
        """
        with self._cache_lock:
            # Ensure list is fresh
            meta, _ = self._ensure_list_fresh()
            return item_id in meta.get("items", {})

    def __len__(self) -> int:
        """
        Return the number of items in the collection.

        Honors list TTL - will fetch fresh data if cache expired.

        Thread-safe (uses per-base-path lock).
        """
        with self._cache_lock:
            # Ensure list is fresh
            meta, _ = self._ensure_list_fresh()
            return len(meta.get("items", {}))

    def keys(self) -> list[str]:
        """
        Return a list of item IDs (keys) in the collection.

        Honors list TTL - will fetch fresh data if cache expired.

        Use all(refresh=True) explicitly if you need to control refresh behavior.

        Thread-safe (uses per-base-path lock).
        """
        with self._cache_lock:
            # Ensure list is fresh
            meta, _ = self._ensure_list_fresh()
            return list(meta.get("items", {}).keys())

    def values(self) -> list[Any]:
        """
        Alias for all(). Returns a list of all items (values) in the collection.

        Supports TTL caching; returns cached data if list TTL not expired.

        Use all(refresh=True) if you need explicit refresh control.
        """
        return self.all()

    def items(self) -> list[tuple[str, Any]]:
        """
        Return a list of (item_id, item_data) tuples.

        Honors list TTL - will fetch fresh data if cache expired.

        Use all(refresh=True) explicitly if you need to control refresh behavior.

        Thread-safe (uses per-base-path lock).
        """
        with self._cache_lock:
            # Ensure list is fresh (single refresh)
            meta, items_list = self._ensure_list_fresh()

            # If just refreshed, extract items into tuples with their IDs
            if items_list is not None:
                result: list[tuple[str, Any]] = []
                for item_obj in items_list:
                    item_id = str(self.id_extractor(item_obj))
                    result.append((item_id, item_obj))
                return result

            # Cache was fresh, load and pair items with their IDs
            item_ids = list(meta.get("items", {}).keys())
            result = []
            for item_id in item_ids:
                item_data = self._load_item_from_file(item_id, meta)
                if item_data is not None:
                    result.append((item_id, item_data))
            return result
