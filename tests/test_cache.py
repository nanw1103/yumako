import time

from yumako.cache import _ram_cache_data, ram_cache


def test_ram_cache_basic():
    """Test basic caching functionality."""
    call_count = 0

    @ram_cache(ttl=1)
    def get_data1():
        nonlocal call_count
        call_count += 1
        return {"value": call_count}

    # First call should execute the function
    result1 = get_data1()
    assert result1["value"] == 1
    assert call_count == 1

    # Second call should use cache
    result2 = get_data1()
    assert result2["value"] == 1
    assert call_count == 1


def test_ram_cache_ttl():
    """Test that cache respects TTL."""
    call_count = 0

    @ram_cache(ttl="1s")
    def get_data2():
        nonlocal call_count
        call_count += 1
        return {"value": call_count}

    # First call
    result1 = get_data2()
    assert result1["value"] == 1
    assert call_count == 1

    # Wait for TTL to expire
    time.sleep(1.1)

    # Should call function again
    result2 = get_data2()
    assert result2["value"] == 2
    assert call_count == 2


def test_ram_cache_different_args():
    """Test that different arguments create different cache entries."""
    call_count = 0

    @ram_cache()
    def get_data3(key: str):
        nonlocal call_count
        call_count += 1
        return {"key": key, "count": call_count}

    # Different args should create different cache entries
    result1 = get_data3("a")
    result2 = get_data3("b")
    result3 = get_data3("a")  # Should use cache

    assert result1["count"] == 1
    assert result2["count"] == 2
    assert result3["count"] == 1  # Same as first call
    assert call_count == 2


def test_ram_cache_none_value():
    """Test caching of None values."""
    call_count = 0

    @ram_cache()
    def get_none():
        nonlocal call_count
        call_count += 1
        return None

    # None values shouldn't be cached
    result1 = get_none()
    assert result1 is None
    assert call_count == 1

    result2 = get_none()
    assert result2 is None
    assert call_count == 2  # Function called again


def test_ram_cache_capacity():
    """Test that LRU eviction works when cache reaches capacity."""
    _ram_cache_data.clear()
    assert len(_ram_cache_data) == 0

    @ram_cache()
    def get_data4(key: str):
        return {"key": key}

    # Fill cache to capacity
    for i in range(_ram_cache_data.capacity * 3):
        get_data4(str(i))

    # Cache should maintain its capacity
    assert len(_ram_cache_data) <= _ram_cache_data.capacity * 2

    # First item should have been evicted
    cache_key = "get_data4:('0',):{}"
    assert cache_key not in _ram_cache_data


def test_ram_cache_with_kwargs():
    """Test caching with keyword arguments."""
    call_count = 0

    @ram_cache()
    def get_data6(*, key: str = "default"):
        nonlocal call_count
        call_count += 1
        return {"key": key, "count": call_count}

    # Different kwarg values should create different cache entries
    result1 = get_data6(key="a")
    result2 = get_data6(key="b")
    result3 = get_data6(key="a")  # Should use cache

    assert result1["count"] == 1
    assert result2["count"] == 2
    assert result3["count"] == 1  # Same as first call
    assert call_count == 2
