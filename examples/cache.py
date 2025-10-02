#!/usr/bin/env -S python3 -W ignore

import os
import time

from yumako import cache


# Example 1: RAM Cache - Fast in-memory caching
@cache.ram_cache(ttl="30s")  # Cache for 30 seconds
def expensive_computation(n):
    """Simulate an expensive computation."""
    print(f"Computing expensive operation for {n}...")
    time.sleep(1)  # Simulate work
    return n * n * n


print("=== RAM Cache Example ===")
print(expensive_computation(5))  # Will compute and cache
print(expensive_computation(5))  # Will use cache (fast!)
print(expensive_computation(3))  # Different args, will compute
print(expensive_computation(3))  # Will use cache


# Example 2: File Cache - Persistent disk-based caching (with RAM cache by default)
@cache.file_cache("cache_data.json", ttl="1m")  # Cache for 1 minute
def fetch_api_data():
    """Simulate fetching data from an API."""
    print("Fetching data from API...")
    time.sleep(2)  # Simulate network delay
    return {"timestamp": time.time(), "data": ["item1", "item2", "item3"], "status": "success"}


print("\n=== File Cache Example (with RAM cache by default) ===")
result1 = fetch_api_data()  # Will fetch and cache to both file and RAM
print(f"First call: {result1}")

result2 = fetch_api_data()  # Will load from RAM cache (fastest)
print(f"Second call: {result2}")


# Example 3: File Cache without RAM Cache (disk-only caching)
@cache.file_cache("cache_disk_only.json", ttl="2m", with_ram_cache=False)
def complex_data_processing():
    """Simulate complex data processing."""
    print("Processing complex data...")
    time.sleep(1)
    return {
        "processed_at": time.time(),
        "result": sum(range(1000)),
        "metadata": {"version": "1.0", "type": "processed"},
    }


print("\n=== File Cache without RAM Cache Example (disk-only) ===")
data1 = complex_data_processing()  # Will process and cache to disk only
print(f"First call: {data1}")

data2 = complex_data_processing()  # Will load from disk cache file
print(f"Second call: {data2}")


# Example 4: Different TTL formats
@cache.ram_cache(ttl="1h")  # 1 hour
def hourly_data():
    return {"hourly": "data", "ttl": "1h"}


@cache.ram_cache(ttl=3600)  # 3600 seconds (same as 1h)
def hourly_data_seconds():
    return {"hourly": "data", "ttl": "3600s"}


@cache.file_cache("daily_cache.json", ttl="1d")  # 1 day
def daily_data():
    return {"daily": "data", "ttl": "1d"}


print("\n=== Different TTL Formats ===")
print(hourly_data())
print(hourly_data_seconds())
print(daily_data())


# Example 5: Cache with function arguments
@cache.ram_cache(ttl="10s")
def calculate_fibonacci(n):
    """Calculate Fibonacci number (with caching)."""
    print(f"Calculating Fibonacci({n})...")
    if n <= 1:
        return n
    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)


print("\n=== Cache with Function Arguments ===")
print(f"Fibonacci(10): {calculate_fibonacci(10)}")
print(f"Fibonacci(10): {calculate_fibonacci(10)}")  # Cached!
print(f"Fibonacci(5): {calculate_fibonacci(5)}")  # Different arg


# Cleanup
if os.path.exists("cache_data.json"):
    os.remove("cache_data.json")
if os.path.exists("cache_disk_only.json"):
    os.remove("cache_disk_only.json")
if os.path.exists("daily_cache.json"):
    os.remove("daily_cache.json")
print("\nCache files cleaned up!")
