import pytest

from yumako.lru import LRUDict, LRUSet


class Item:
    """Test class that supports weak references."""

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        if not isinstance(other, Item):
            return False
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return f"Item({self.value})"


class Value:
    """Test class that supports weak references for LRUDict testing."""

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        if not isinstance(other, Value):
            return False
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return f"Value({self.value})"


def test_set_init():
    """Test initialization and capacity validation."""
    # Valid initialization
    lru = LRUSet(capacity=5)
    assert len(lru) == 0
    assert lru.capacity == 5

    # Invalid capacity
    with pytest.raises(TypeError):
        LRUSet(capacity="5")
    with pytest.raises(ValueError):
        LRUSet(capacity=0)
    with pytest.raises(ValueError):
        LRUSet(capacity=-1)


def test_set_add_and_contains():
    """Test adding items and checking containment."""
    capacity = 3
    lru = LRUSet(capacity=capacity)
    items = [Item(i) for i in range(4)]

    # Basic add and contains
    lru.add(items[0])
    assert items[0] in lru
    assert len(lru) <= capacity

    # Add up to capacity
    lru.add(items[1])
    lru.add(items[2])
    assert len(lru) <= capacity

    # Add beyond capacity
    lru.add(items[3])
    assert len(lru) <= capacity * 2
    assert items[3] in lru


def test_set_weak_reference():
    """Test weak reference behavior."""
    capacity = 3
    lru = LRUSet(capacity=capacity)
    item1 = Item(1)
    item2 = Item(2)

    # Add items
    lru.add(item1)
    lru.add(item2)
    assert len(lru) <= capacity

    # Delete reference to item1
    del item1
    import gc

    gc.collect()
    assert len(lru) <= capacity

    # Verify item2 still exists
    assert item2 in lru


def test_set_discard():
    """Test discard operation."""
    capacity = 3
    lru = LRUSet(capacity=capacity)
    item1 = Item(1)
    item2 = Item(2)

    # Discard from empty set
    lru.discard(item1)  # Should not raise
    assert len(lru) == 0

    # Add and discard
    lru.add(item1)
    lru.add(item2)
    assert len(lru) <= capacity

    lru.discard(item1)
    assert len(lru) <= capacity
    assert item1 not in lru
    assert item2 in lru

    # Discard non-existent item
    lru.discard(item1)  # Should not raise
    assert len(lru) <= capacity


def test_set_iteration():
    """Test set iteration."""
    capacity = 3
    lru = LRUSet(capacity=capacity)
    items = [Item(i) for i in range(3)]

    # Add items
    for item in items:
        lru.add(item)

    assert len(lru) <= capacity
    assert set(lru) == set(items)


def test_set_clear():
    """Test clear operation."""
    capacity = 3
    lru = LRUSet(capacity=capacity)
    items = [Item(i) for i in range(3)]
    for item in items:
        lru.add(item)

    assert len(lru) <= capacity
    lru.clear()
    assert len(lru) == 0
    assert list(lru) == []


def test_set_non_weakrefable():
    """Test adding non-weakrefable items."""
    lru = LRUSet(capacity=2)

    # These should raise TypeError
    with pytest.raises(TypeError):
        lru.add("string")
    with pytest.raises(TypeError):
        lru.add(42)
    with pytest.raises(TypeError):
        lru.add((1, 2, 3))


def test_set_concurrent_modification():
    """Test behavior when modifying during iteration."""
    lru = LRUSet(capacity=3)
    items = [Item(i) for i in range(3)]
    for item in items:
        lru.add(item)

    # Modify during iteration
    with pytest.raises(RuntimeError):
        for _ in lru:
            lru.add(Item(10))


def test_set_stress():
    """Test with larger number of items and operations."""
    capacity = 1000
    lru = LRUSet(capacity=capacity)
    items = [Item(i) for i in range(capacity * 3)]

    # Add items beyond capacity
    for item in items:
        lru.add(item)

    assert len(lru) <= capacity * 2
    assert items[0] not in lru  # First items should be evicted
    assert items[-1] in lru  # Last items should remain


def test_set_weak_reference_chain():
    """Test weak reference behavior with chain of references."""
    lru = LRUSet(capacity=3)

    class Container:
        def __init__(self, item):
            self.item = item

    item1 = Item(1)
    container = Container(item1)

    lru.add(item1)
    assert len(lru) == 1

    # Removing direct reference but keeping container reference
    del item1
    import gc

    gc.collect()
    assert len(lru) == 1  # Should still exist due to container reference

    # Remove container reference
    del container
    gc.collect()
    assert len(lru) == 0


def test_set_edge_cases():
    """Test various edge cases."""
    lru = LRUSet(capacity=2)
    item1 = Item(1)

    # Test empty operations
    assert len(lru) == 0

    # Test single item operations
    lru.add(item1)

    # Test duplicate adds with access in between
    lru.add(item1)
    assert item1 in lru
    lru.add(item1)
    assert len(lru) == 1


def test_set_memory_leak():
    """Test for memory leaks."""
    import gc

    # Force collection before we start
    gc.collect()
    initial_size = len(gc.get_objects())

    def run_test():
        lru = LRUSet(capacity=100)
        items = []  # Keep references during the test

        # Add and remove many items
        for i in range(1000):
            item = Item(i)
            items.append(item)  # Keep reference to prevent premature collection
            lru.add(item)
            if i % 2 == 0:
                lru.discard(item)

        # Clear all references explicitly
        items.clear()
        lru.clear()
        del lru

    # Run the test in its own scope
    run_test()

    # Force garbage collection multiple times to ensure cleanup
    for _ in range(3):
        gc.collect()

    final_size = len(gc.get_objects())

    # The difference should be very small now
    diff = final_size - initial_size
    assert diff < 50, f"Memory leak detected: {diff} objects remaining"


# LRUDict Tests
def test_dict_init():
    """Test initialization and capacity validation."""
    # Valid initialization
    lru = LRUDict(capacity=5)
    assert len(lru) == 0
    assert lru.capacity == 5

    # Invalid capacity
    with pytest.raises(TypeError):
        LRUDict(capacity="5")
    with pytest.raises(ValueError):
        LRUDict(capacity=0)
    with pytest.raises(ValueError):
        LRUDict(capacity=-1)


def test_dict_setitem_getitem():
    """Test setting and getting items."""
    capacity = 3
    lru = LRUDict(capacity=capacity)
    values = [Value(i) for i in range(4)]

    # Add items up to capacity
    for i in range(3):
        lru[str(i)] = values[i]
        assert lru[str(i)] == values[i]
    assert len(lru) <= capacity

    # Add beyond capacity
    lru["3"] = values[3]
    assert len(lru) <= capacity * 2
    assert lru["3"] == values[3]


def test_dict_weak_reference():
    """Test weak reference behavior."""
    capacity = 3
    lru = LRUDict(capacity=capacity)
    val1 = Value(1)
    val2 = Value(2)

    # Add items
    lru["a"] = val1
    lru["b"] = val2
    assert len(lru) <= capacity

    # Delete reference to val1
    del val1
    import gc

    gc.collect()
    assert len(lru) <= capacity * 2
    assert "b" in lru


def test_dict_get():
    """Test dictionary get method."""
    capacity = 3
    lru = LRUDict(capacity=capacity)
    values = [Value(i) for i in range(3)]

    # Test get on empty dict
    assert lru.get("0") is None
    assert lru.get("0", default=values[0]) == values[0]

    # Add and get
    lru["0"] = values[0]
    assert lru.get("0") == values[0]
    assert lru.get("missing") is None
    assert len(lru) <= capacity


def test_set_operations():
    """Test set comparison operations."""
    capacity = 3
    lru = LRUSet(capacity=capacity)
    items = [Item(i) for i in range(3)]

    # Create reference sets
    empty_set = set()
    full_set = {items[0], items[1], items[2]}
    subset = {items[0], items[1]}

    # Test empty set
    assert lru <= empty_set
    assert lru < full_set
    assert not lru >= full_set
    assert not lru > empty_set
    assert lru.isdisjoint(full_set)

    # Add items
    lru.add(items[0])
    lru.add(items[1])

    # Test with items
    assert lru <= full_set
    assert not lru < subset
    assert lru >= subset
    assert not lru > full_set
    assert not lru.isdisjoint(subset)

    # Test equality
    other_lru = LRUSet(capacity=capacity)
    other_lru.add(items[0])
    other_lru.add(items[1])
    assert lru == other_lru


def test_dict_str_repr():
    """Test string representations."""
    capacity = 3
    lru = LRUDict(capacity=capacity, weak=False)
    values = [Value(i) for i in range(2)]

    # Empty dict
    assert repr(lru) == f"LRUDict(capacity={capacity}, weak=False, size=0)"
    assert str(lru) == "{}"

    # With items
    lru["0"] = values[0]
    lru["1"] = values[1]
    assert repr(lru) == f"LRUDict(capacity={capacity}, weak=False, size=2)"
    # str() should show all items but order may vary
    str_result = str(lru)
    assert "'0'" in str_result and "'1'" in str_result


def test_dict_memory_leak():
    """Test for memory leaks."""
    import gc

    lru = LRUDict(capacity=100)
    initial_size = len(gc.get_objects())

    # Add and remove many items
    for i in range(1000):
        val = Value(i)
        lru[str(i)] = val
        if i % 2 == 0:
            lru.popitem()

    # Force garbage collection
    gc.collect()
    final_size = len(gc.get_objects())

    # Check that we haven't leaked objects
    assert final_size - initial_size < 200  # Allow some overhead


def test_dict_stress():
    """Test with larger number of items and operations."""
    capacity = 1000
    lru = LRUDict(capacity=capacity)
    values = [Value(i) for i in range(capacity * 3)]

    # Add items beyond capacity
    for i, val in enumerate(values):
        lru[str(i)] = val

    assert len(lru) <= capacity * 2
    assert "0" not in lru  # First items should be evicted
    assert str(capacity * 2 - 1) in lru  # Last items should remain


def test_dict_weak_reference_chain():
    """Test weak reference behavior with chain of references."""
    lru = LRUDict(capacity=3)

    class Container:
        def __init__(self, value):
            self.value = value

    val1 = Value(1)
    container = Container(val1)

    lru["a"] = val1
    assert len(lru) == 1

    # Removing direct reference but keeping container reference
    del val1
    import gc

    gc.collect()
    assert len(lru) == 1  # Should still exist due to container reference

    # Remove container reference
    del container
    gc.collect()
    assert len(lru) == 0


def test_dict_edge_cases():
    """Test various edge cases."""
    lru = LRUDict(capacity=2)
    val1 = Value(1)

    # Test empty operations
    assert len(lru) == 0

    # Test single item operations
    lru["a"] = val1

    # Test update existing key
    val2 = Value(2)
    lru["a"] = val2
    assert len(lru) == 1
    assert lru["a"] == val2


def test_dict_update():
    """Test update method behavior."""
    capacity = 3
    lru = LRUDict(capacity=capacity)
    val1 = Value(1)
    val2 = Value(2)
    val3 = Value(3)
    val4 = Value(4)

    # Test different update patterns
    # 1. Update empty dict
    lru.update({"a": val1})
    assert len(lru) <= capacity
    assert lru["a"] == val1

    # 2. Update with multiple items
    lru.update({"b": val2, "c": val3})
    assert len(lru) <= capacity
    assert lru["b"] == val2
    assert lru["c"] == val3

    # 3. Update with kwargs
    lru.update(d=val4)
    assert len(lru) <= capacity * 2
    assert lru["d"] == val4

    # 4. Mixed update
    lru.update({"e": val1}, f=val2)
    assert len(lru) <= capacity * 2
    assert lru["e"] == val1
    assert lru["f"] == val2

    # Verify size constraint
    assert len(lru) <= capacity * 2
    lru.update({"g": val3})
    assert len(lru) <= capacity * 3
    assert "a" not in lru


def test_dict_delete():
    """Test delete operations."""
    lru = LRUDict(capacity=3)
    val1 = Value(1)
    val2 = Value(2)

    lru["a"] = val1
    lru["b"] = val2

    # Test del
    del lru["a"]
    assert "a" not in lru
    assert len(lru) == 1

    # Test del non-existent
    del lru["nonexistent"]  # Should not raise since pop(key, None) is used


def test_dict_contains():
    """Test contains operation."""
    lru = LRUDict(capacity=3)
    val1 = Value(1)
    val2 = Value(2)
    val3 = Value(3)

    lru["a"] = val1
    lru["b"] = val2
    lru["c"] = val3

    # Test contains
    assert "b" in lru
    assert "d" not in lru


def test_dict_clear_references():
    """Test that clear properly removes all references."""
    import gc

    lru = LRUDict(capacity=3)
    val1 = Value(1)
    val2 = Value(2)

    lru["a"] = val1
    lru["b"] = val2

    # Clear dictionary
    lru.clear()
    assert len(lru) == 0

    # Delete original references
    del val1
    del val2
    gc.collect()

    # Verify no references remain
    assert len(lru) == 0


def test_set_mixed_operations():
    """Test complex sequences of mixed operations on LRUSet."""
    lru = LRUSet(capacity=3)
    items = [Item(i) for i in range(5)]

    # Sequence 1: add-access-add pattern
    lru.add(items[0])
    lru.add(items[1])
    assert items[0] in lru  # Access to change order
    lru.add(items[2])
    assert items[0] in lru  # items[0] should remain due to recent access
    assert items[1] in lru
    assert items[2] in lru

    # Sequence 2: add-discard-add pattern
    lru.discard(items[1])
    lru.add(items[3])
    assert items[3] in lru

    lru.add(items[4])

    # Verify final state
    assert items[2] in lru
    assert items[3] in lru
    assert items[4] in lru


def test_set_dict_interaction():
    """Test interaction between LRUSet and LRUDict with shared objects."""
    set_lru = LRUSet(capacity=3)
    dict_lru = LRUDict(capacity=3)

    # Create shared objects
    items = [Item(i) for i in range(3)]
    values = [Value(item.value) for item in items]  # Keep references to values

    # Add to both containers
    for i, (item, value) in enumerate(zip(items, values)):
        set_lru.add(item)
        dict_lru[str(i)] = value
        print(f"After adding {i}:")
        print(f"  set_lru: {set_lru}")
        print(f"  dict_lru: {dict_lru}")
        print(f"  dict_lru keys: {list(dict_lru.keys())}")
        print(f"  dict_lru values: {list(dict_lru.values())}")

    # Verify independent operation
    assert len(set_lru) == len(dict_lru) == 3


def test_set_empty_operations():
    """Test operations on empty LRUSet."""
    lru = LRUSet(capacity=3)

    # Empty set operations
    assert len(lru) == 0
    assert list(lru) == []


def test_dict_empty_operations():
    """Test operations on empty LRUDict."""
    lru = LRUDict(capacity=3)

    # Empty dict operations
    assert len(lru) == 0
    assert dict(lru) == {}


def test_set_invalid_capacity():
    """Test invalid capacity values for LRUSet."""
    with pytest.raises(TypeError):
        LRUSet(capacity="3")
    with pytest.raises(ValueError):
        LRUSet(capacity=0)
    with pytest.raises(ValueError):
        LRUSet(capacity=-1)


def test_dict_invalid_capacity():
    """Test invalid capacity values for LRUDict."""
    with pytest.raises(TypeError):
        LRUDict(capacity="3")
    with pytest.raises(ValueError):
        LRUDict(capacity=0)
    with pytest.raises(ValueError):
        LRUDict(capacity=-1)


def test_set_basic_types():
    """Test LRUSet with basic Python types."""
    # Should raise TypeError for non-referenceable types
    lru = LRUSet(capacity=3, weak=False)
    lru.add(42)
    lru.add("string")
    lru.add((1, 2, 3))
    assert len(lru) == 3
    assert 42 in lru
    assert "string" in lru
    assert (1, 2, 3) in lru


def test_set_basic_types_weak():
    """Test LRUSet with basic Python types."""
    # Should raise TypeError for non-referenceable types
    lru = LRUSet(capacity=3)

    with pytest.raises(TypeError):
        lru.add(42)  # int is not weakref-able

    with pytest.raises(TypeError):
        lru.add("string")  # str is not weakref-able

    with pytest.raises(TypeError):
        lru.add((1, 2, 3))  # tuple is not weakref-able

    # Test with types that support weak references
    class WeakRefSupported:
        def __init__(self, value):
            self.value = value

    lru = LRUSet(capacity=3)
    items = [WeakRefSupported(i) for i in range(3)]

    for item in items:
        lru.add(item)

    assert len(lru) == 3
    assert items[0] in lru


def test_dict_basic_types():
    """Test LRUDict with basic Python types as values."""
    lru = LRUDict(capacity=3, weak=False)

    # Basic types as keys (should work)
    lru[42] = Value(1)  # int key
    lru["string"] = Value(2)  # str key
    lru[(1, 2)] = Value(3)  # tuple key

    assert len(lru) == 3
    assert 42 in lru
    assert "string" in lru
    assert (1, 2) in lru

    # Basic types as values
    lru["a"] = 42
    lru["b"] = "string"
    lru["c"] = (1, 2, 3)

    # Test with proper value type
    lru["d"] = Value(4)
    assert lru["d"].value == 4


def test_dict_basic_types_weak():
    """Test LRUDict with basic Python types as values."""
    lru = LRUDict(capacity=3, weak=True)

    v1 = Value(1)
    v2 = Value(2)
    v3 = Value(3)
    # Basic types as keys (should work)
    lru[42] = v1  # int key
    lru["string"] = v2  # str key
    lru[(1, 2)] = v3  # tuple key

    assert len(lru) == 3
    assert 42 in lru
    assert "string" in lru
    assert (1, 2) in lru

    # Basic types as values (should raise TypeError)
    with pytest.raises(TypeError):
        lru["a"] = 42  # int is not weakref-able

    with pytest.raises(TypeError):
        lru["b"] = "string"  # str is not weakref-able

    with pytest.raises(TypeError):
        lru["c"] = (1, 2, 3)  # tuple is not weakref-able

    # Test with proper value type
    lru["d"] = Value(4)
    v = lru.get("d", None)
    if v is not None:
        assert v.value == 4


def test_dict_clear():
    """Test clear operation."""
    capacity = 3
    lru = LRUDict(capacity=capacity)
    values = [Value(i) for i in range(3)]
    for i, val in enumerate(values):
        lru[str(i)] = val

    assert len(lru) <= capacity
    lru.clear()
    assert len(lru) == 0
    assert dict(lru) == {}


def test_dict_iteration():
    """Test dictionary iteration methods."""
    capacity = 3
    lru = LRUDict(capacity=capacity)
    values = [Value(i) for i in range(3)]

    # Add items
    for i, val in enumerate(values):
        lru[str(i)] = val

    assert len(lru) <= capacity

    # Test keys
    assert set(lru.keys()) == {"0", "1", "2"}

    # Test values
    assert set(lru.values()) == set(values)

    # Test items
    assert set(lru.items()) == {("0", values[0]), ("1", values[1]), ("2", values[2])}
