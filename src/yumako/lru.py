from collections import ChainMap
from collections.abc import ItemsView, Iterator, KeysView, MutableMapping, MutableSet, ValuesView
from typing import TypeVar, cast
from weakref import WeakSet, WeakValueDictionary

T = TypeVar("T")  # Item type for Set
K = TypeVar("K")  # Key type
V = TypeVar("V")  # Value type


class LRUSet(MutableSet[T]):
    """A Least Recently Used (LRU) Set with weak references and fixed capacity.

    Implementation:
        Uses two set caches for O(1) operations:
        - new_cache: holds recently used items
        - old_cache: holds less recently used items

        When new_cache reaches capacity:
        1. old_cache becomes the current new_cache
        2. new_cache is reset empty

        On item access:
        1. Check new_cache first (fast path)
        2. If not found, check old_cache
        3. If found in old_cache, promote to new_cache

    Performance:
        - add: O(1)
        - contains: O(1)
        - discard: O(1)
        - len: O(1)
        - iter: O(n)

    Memory:
        - If weak=true, uses weak references, items may be garbage collected
        - Maximum memory: 2 * capacity items

    Thread Safety:
        - Not thread-safe
        - Use external synchronization if needed

    Args:
        capacity: Maximum items per cache. Must be positive integer.

    Example:
        >>> class Item:
        ...     def __init__(self, value): self.value = value
        >>> lru = LRUSet(capacity=2)
        >>> items = [Item(i) for i in range(3)]
        >>> lru.add(items[0])      # new_cache: [0]
        >>> lru.add(items[1])      # new_cache: [0,1]
        >>> items[0] in lru        # promotes 0: [1,0]
        >>> lru.add(items[2])      # rotates: old=[1,0], new=[2]
    """

    _capacity: int
    _new_cache: MutableSet[T]
    _old_cache: MutableSet[T]

    def __init__(self, capacity: int = 32, weak: bool = False) -> None:
        if not isinstance(capacity, int):
            raise TypeError("capacity must be an integer")
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        self._capacity = capacity
        self._weak = weak
        self._new_cache = WeakSet() if weak else set()  # Recently used items
        self._old_cache = WeakSet() if weak else set()  # Less recently used items

    def add(self, item: T) -> None:
        """Add an item to the set."""
        # If item exists in new_cache, we're done
        if item in self._new_cache:
            return

        # Add to new_cache
        self._new_cache.add(item)

        # If size exceeds capacity, rotate caches
        if not self._ensure_rotation():
            # Remove from old_cache if present
            self._old_cache.discard(item)

    def discard(self, item: T) -> None:
        """Remove an item from the set if it exists."""
        self._new_cache.discard(item)
        self._old_cache.discard(item)

    def __contains__(self, item: object) -> bool:
        """Check if an item is in the set."""
        if item in self._new_cache:
            return True

        if item in self._old_cache:
            # Promote to new_cache
            item_t = cast(T, item)  # Safe cast since we checked type above
            self._new_cache.add(item_t)

            if not self._ensure_rotation():
                self._old_cache.discard(item_t)
            return True

        return False

    def _ensure_rotation(self) -> bool:
        """Rotate caches if necessary."""
        if len(self._new_cache) <= self._capacity:
            return False
        self._old_cache = self._new_cache
        self._new_cache = WeakSet() if self._weak else set()
        return True

    def __len__(self) -> int:
        """Return total number of items across both caches."""
        return len(self._new_cache) + len(self._old_cache)

    def __iter__(self) -> Iterator[T]:
        """Iterate over all items in the set."""
        # Yield from new_cache first
        yield from self._new_cache

        # Then yield from old_cache (skipping duplicates)
        yield from self._old_cache

    def clear(self) -> None:
        """Remove all items from the set."""
        self._new_cache.clear()
        self._old_cache.clear()

    @property
    def capacity(self) -> int:
        """Get the capacity of each cache."""
        return self._capacity

    def __repr__(self) -> str:
        """Return a string representation of the set.

        Format: LRUSet(capacity=N)
        """
        return f"{type(self).__name__}(capacity={self._capacity}, weak={self._weak}, size={len(self)})"

    def __str__(self) -> str:
        """Return a string of the set contents.

        Format: {item1, item2, ...}
        """
        items = ", ".join(str(item) for item in self)
        return "{" + items + "}"


class LRUDict(MutableMapping[K, V]):
    """A Least Recently Used (LRU) Dictionary with weak references and fixed capacity.

    Implementation:
        Uses two dictionary caches for O(1) operations:
        - new_cache: holds recently used items
        - old_cache: holds less recently used items

        When new_cache reaches capacity:
        1. old_cache becomes the current new_cache
        2. new_cache is reset empty

        On key access:
        1. Check new_cache first (fast path)
        2. If not found, check old_cache
        3. If found in old_cache, promote to new_cache

    Performance:
        - get/set: O(1)
        - contains: O(1)
        - delete: O(1)
        - len: O(1)
        - iter: O(n)

    Memory:
        - If weak is true, uses weak references for values, may be garbage collected
        - Keys are stored strongly
        - Maximum memory: 2 * capacity items

    Thread Safety:
        - Not thread-safe
        - Use external synchronization if needed

    Args:
        capacity: Maximum items per cache. Must be positive integer.

    Example:
        >>> class Value:
        ...     def __init__(self, x): self.x = x
        >>> lru = LRUDict(capacity=2)
        >>> v1, v2, v3 = Value(1), Value(2), Value(3)
        >>> lru['a'] = v1         # new_cache: {'a':v1}
        >>> lru['b'] = v2         # new_cache: {'a':v1, 'b':v2}
        >>> _ = lru['a']          # promotes 'a': {'b':v2, 'a':v1}
        >>> lru['c'] = v3         # rotates: old={'b':v2, 'a':v1}, new={'c':v3}
    """

    _capacity: int
    _weak: bool
    _new_cache: MutableMapping[K, V]
    _old_cache: MutableMapping[K, V]

    def __init__(self, capacity: int = 32, weak: bool = False) -> None:
        if not isinstance(capacity, int):
            raise TypeError("capacity must be an integer")
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        self._capacity = capacity
        self._weak = weak
        self._new_cache = WeakValueDictionary() if weak else dict()
        self._old_cache = WeakValueDictionary() if weak else dict()

    def _ensure_rotation(self) -> bool:
        """Rotate caches if necessary."""
        if len(self._new_cache) <= self._capacity:
            return False
        self._old_cache = self._new_cache
        self._new_cache = WeakValueDictionary() if self._weak else dict()
        return True

    def __setitem__(self, key: K, value: V) -> None:
        if key in self._new_cache:
            self._new_cache[key] = value
            return

        self._new_cache[key] = value

        # If size exceeds capacity, rotate caches
        if not self._ensure_rotation():
            # Remove from old_cache if present
            self._old_cache.pop(key, None)

    def __getitem__(self, key: K) -> V:
        # Check new_cache first
        try:
            return self._new_cache[key]
        except KeyError:
            # Check old_cache and promote if found
            value = self._old_cache[key]
            # Promote to new_cache
            self._new_cache[key] = value

            # If size exceeds capacity, rotate caches
            if not self._ensure_rotation():
                self._old_cache.pop(key, None)

            return value

    def __delitem__(self, key: K) -> None:
        """Remove an item from either cache."""
        self._new_cache.pop(key, None)
        self._old_cache.pop(key, None)

    def __len__(self) -> int:
        return len(self._new_cache) + len(self._old_cache)

    def __contains__(self, key: object) -> bool:
        """Return True if key exists in the dictionary."""
        key_k = cast(K, key)  # Safe cast since we checked type above
        return key_k in self._new_cache or key_k in self._old_cache

    def __iter__(self) -> Iterator[K]:
        yield from self._new_cache
        yield from self._old_cache

    def clear(self) -> None:
        self._new_cache.clear()
        self._old_cache.clear()

    @property
    def capacity(self) -> int:
        return self._capacity

    def items(self) -> ItemsView[K, V]:
        """Iterate over (key, value) pairs in LRU order."""
        # Create a dict view directly from the caches without intermediate dicts
        combined = ChainMap(self._new_cache, self._old_cache)
        return ItemsView(combined)

    def keys(self) -> KeysView[K]:
        """Iterate over keys in LRU order."""
        combined = ChainMap(self._new_cache, self._old_cache)
        return KeysView(combined)

    def values(self) -> ValuesView[V]:
        """Iterate over values in LRU order."""
        combined = ChainMap(self._new_cache, self._old_cache)
        return ValuesView(combined)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(capacity={self._capacity}, weak={self._weak}, size={len(self)})"

    def __str__(self) -> str:
        return str(dict(self.items()))

    def popitem(self) -> tuple[K, V]:
        """Remove and return the most recently used item.

        Returns:
            tuple: A (key, value) pair from new_cache

        Raises:
            KeyError: If dictionary is empty
        """
        if not self:
            raise KeyError("dictionary is empty")

        try:
            # Try to pop from new_cache first
            key = next(iter(self._new_cache))
            value = self._new_cache[key]
            del self._new_cache[key]
            return key, value
        except (StopIteration, KeyError):
            # If new_cache is empty, pop from old_cache
            key = next(iter(self._old_cache))
            value = self._old_cache[key]
            del self._old_cache[key]
            return key, value
