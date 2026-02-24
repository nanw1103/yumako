import json
import os
import shutil
import tempfile
import threading
import time

import pytest

from yumako.cache import FileCollection


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp = tempfile.mkdtemp()
    yield temp
    # Cleanup
    if os.path.exists(temp):
        shutil.rmtree(temp)


@pytest.fixture
def sample_data():
    """Sample collection data."""
    return [
        {"id": "user1", "name": "Alice", "age": 30},
        {"id": "user2", "name": "Bob", "age": 25},
        {"id": "user3", "name": "Charlie", "age": 35},
    ]


class TestFileCollectionBasics:
    """Test basic FileCollection functionality."""

    def test_init_creates_directory(self, temp_dir):
        """Test that FileCollection creates the base directory."""
        collection_path = os.path.join(temp_dir, "collection")
        assert not os.path.exists(collection_path)

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: [],
            get_fn=lambda x: None,
        )

        assert os.path.exists(collection_path)
        collection.clear()

    def test_init_rejects_root_directory(self, temp_dir):
        """Test that FileCollection rejects the root directory."""
        with pytest.raises(ValueError, match="root directory"):
            FileCollection(
                base_path="/",
                list_fn=lambda: [],
                get_fn=lambda x: None,
            )

    def test_init_validates_ttl_order(self, temp_dir):
        """Test that ttl_item must be >= ttl_list."""
        collection_path = os.path.join(temp_dir, "collection")

        with pytest.raises(ValueError, match="ttl_item must be >= ttl_list"):
            FileCollection(
                base_path=collection_path,
                list_fn=lambda: [],
                get_fn=lambda x: None,
                ttl_list="10m",
                ttl_item="1m",  # Less than ttl_list
            )

    def test_all_empty_collection(self, temp_dir):
        """Test retrieving all items from an empty collection."""
        collection_path = os.path.join(temp_dir, "collection")

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: [],
            get_fn=lambda x: None,
        )

        result = collection.all()
        assert result == []
        collection.clear()

    def test_all_with_data(self, temp_dir, sample_data):
        """Test retrieving all items from a collection."""
        collection_path = os.path.join(temp_dir, "collection")

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: None,
        )

        result = collection.all()
        assert len(result) == 3
        assert result == sample_data
        collection.clear()

    def test_get_specific_item(self, temp_dir, sample_data):
        """Test retrieving a specific item."""
        collection_path = os.path.join(temp_dir, "collection")
        data_lookup = {item["id"]: item for item in sample_data}

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: data_lookup.get(x),
        )

        result = collection.get("user1")
        assert result == sample_data[0]
        collection.clear()

    def test_get_nonexistent_item(self, temp_dir):
        """Test retrieving a nonexistent item."""
        collection_path = os.path.join(temp_dir, "collection")

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: [],
            get_fn=lambda x: None,
        )

        result = collection.get("nonexistent")
        assert result is None
        collection.clear()

    def test_contains(self, temp_dir, sample_data):
        """Test the __contains__ method."""
        collection_path = os.path.join(temp_dir, "collection")

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: None,
        )

        assert "user1" in collection
        assert "user2" in collection
        assert "nonexistent" not in collection
        collection.clear()

    def test_len(self, temp_dir, sample_data):
        """Test the __len__ method."""
        collection_path = os.path.join(temp_dir, "collection")

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: None,
        )

        assert len(collection) == 3
        collection.clear()

    def test_keys(self, temp_dir, sample_data):
        """Test the keys() method."""
        collection_path = os.path.join(temp_dir, "collection")

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: None,
        )

        keys = collection.keys()
        assert set(keys) == {"user1", "user2", "user3"}
        collection.clear()

    def test_values(self, temp_dir, sample_data):
        """Test the values() method."""
        collection_path = os.path.join(temp_dir, "collection")

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: None,
        )

        values = collection.values()
        assert values == sample_data
        collection.clear()

    def test_items(self, temp_dir, sample_data):
        """Test the items() method."""
        collection_path = os.path.join(temp_dir, "collection")

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: None,
        )

        items = collection.items()
        assert len(items) == 3
        assert items[0] == ("user1", sample_data[0])
        assert items[1] == ("user2", sample_data[1])
        assert items[2] == ("user3", sample_data[2])
        collection.clear()

    def test_subscript_access(self, temp_dir, sample_data):
        """Test subscript access with __getitem__."""
        collection_path = os.path.join(temp_dir, "collection")
        data_lookup = {item["id"]: item for item in sample_data}

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: data_lookup.get(x),
        )

        assert collection["user1"] == sample_data[0]

        with pytest.raises(KeyError):
            _ = collection["nonexistent"]

        collection.clear()

    def test_iteration(self, temp_dir, sample_data):
        """Test iteration over collection."""
        collection_path = os.path.join(temp_dir, "collection")

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: None,
        )

        items = list(collection)
        assert items == sample_data
        collection.clear()


class TestFileCollectionTTL:
    """Test TTL (Time-To-Live) functionality."""

    def test_list_ttl_cache_hit(self, temp_dir, sample_data):
        """Test that list cache is used when TTL hasn't expired."""
        collection_path = os.path.join(temp_dir, "collection")
        call_count = {"list": 0}

        def list_fn():
            call_count["list"] += 1
            return sample_data

        collection = FileCollection(
            base_path=collection_path,
            list_fn=list_fn,
            get_fn=lambda x: None,
            ttl_list="1h",  # Long TTL
        )

        # First call should call list_fn
        collection.all()
        assert call_count["list"] == 1

        # Second call should use cache
        collection.all()
        assert call_count["list"] == 1

        collection.clear()

    def test_list_ttl_expiration(self, temp_dir, sample_data):
        """Test that list cache refreshes when TTL expires."""
        collection_path = os.path.join(temp_dir, "collection")
        call_count = {"list": 0}

        def list_fn():
            call_count["list"] += 1
            return sample_data

        collection = FileCollection(
            base_path=collection_path,
            list_fn=list_fn,
            get_fn=lambda x: None,
            ttl_list="1s",  # Short TTL
        )

        # First call
        collection.all()
        assert call_count["list"] == 1

        # Wait for TTL to expire
        time.sleep(1.1)

        # Should refresh
        collection.all()
        assert call_count["list"] == 2

        collection.clear()

    def test_force_refresh_list(self, temp_dir, sample_data):
        """Test refresh parameter for list."""
        collection_path = os.path.join(temp_dir, "collection")
        call_count = {"list": 0}

        def list_fn():
            call_count["list"] += 1
            return sample_data

        collection = FileCollection(
            base_path=collection_path,
            list_fn=list_fn,
            get_fn=lambda x: None,
            ttl_list="1h",  # Long TTL
        )

        # First call
        collection.all()
        assert call_count["list"] == 1

        # refresh should bypass cache
        collection.all(refresh=True)
        assert call_count["list"] == 2

        collection.clear()

    def test_item_ttl_expiration(self, temp_dir, sample_data):
        """Test that item cache respects TTL."""
        collection_path = os.path.join(temp_dir, "collection")
        data_lookup = {item["id"]: item for item in sample_data}
        call_count = {"get": 0}

        def get_fn(item_id):
            call_count["get"] += 1
            return data_lookup.get(item_id)

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=get_fn,
            ttl_list="1s",
            ttl_item="1s",  # Same TTL for both
        )

        # First call
        collection.get("user1")
        assert call_count["get"] == 1

        # Immediate call should use cache
        collection.get("user1")
        assert call_count["get"] == 1

        # Wait for TTL to expire
        time.sleep(1.1)

        # Should refresh
        collection.get("user1")
        assert call_count["get"] == 2

        collection.clear()


class TestFileCollectionLRU:
    """Test LRU cache functionality."""

    def test_lru_basic(self, temp_dir, sample_data):
        """Test basic LRU caching."""
        collection_path = os.path.join(temp_dir, "collection")
        data_lookup = {item["id"]: item for item in sample_data}

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: data_lookup.get(x),
            lru_capacity=10,
        )

        # Get item multiple times
        collection.get("user1")
        collection.get("user1")

        # Most recent item should be in LRU cache
        assert collection.lru is not None
        assert "user1" in collection.lru

        collection.clear()

    def test_lru_enabled_by_default(self, temp_dir, sample_data):
        """Test that LRU cache is enabled by default with capacity 1000."""
        collection_path = os.path.join(temp_dir, "collection")
        data_lookup = {item["id"]: item for item in sample_data}

        # Create collection without specifying lru_capacity
        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: data_lookup.get(x),
        )

        # LRU should be enabled by default
        assert collection.lru is not None

        # Get item and verify it's cached
        collection.get("user1")
        assert "user1" in collection.lru

        collection.clear()

    def test_lru_shared_between_instances(self, temp_dir, sample_data):
        """Test that LRU cache is shared between instances with same base_path."""
        collection_path = os.path.join(temp_dir, "collection")
        data_lookup = {item["id"]: item for item in sample_data}

        collection1 = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: data_lookup.get(x),
            lru_capacity=10,
        )

        collection2 = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: data_lookup.get(x),
            lru_capacity=10,
        )

        # Add to cache via collection1
        collection1.get("user1")

        # Should be accessible via collection2
        assert collection2.lru is collection1.lru
        assert "user1" in collection2.lru

        collection1.clear()

    def test_no_lru_when_disabled(self, temp_dir, sample_data):
        """Test that LRU cache is disabled when capacity is 0."""
        collection_path = os.path.join(temp_dir, "collection")

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: None,
            lru_capacity=0,
        )

        assert collection.lru is None

        collection.clear()


class TestFileCollectionIDSanitization:
    """Test ID sanitization for filesystem compatibility."""

    def test_sanitize_problematic_characters(self, temp_dir):
        """Test that problematic characters are sanitized."""
        collection_path = os.path.join(temp_dir, "collection")
        data = [
            {"id": "file/with/slashes", "value": 1},
            {"id": "file:with:colons", "value": 2},
            {"id": "file*with*asterisks", "value": 3},
        ]
        data_lookup = {item["id"]: item for item in data}

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: data,
            get_fn=lambda x: data_lookup.get(x),
        )

        # Refresh list to save items
        collection.all()

        # All items should be retrievable by original ID
        assert collection.get("file/with/slashes") == data[0]
        assert collection.get("file:with:colons") == data[1]
        assert collection.get("file*with*asterisks") == data[2]

        # Check that files were created with sanitized names
        files = os.listdir(collection_path)
        assert len([f for f in files if f.endswith(".json")]) == 3

        collection.clear()

    def test_id_map_stores_sanitization(self, temp_dir):
        """Test that id_map stores sanitization mapping."""
        collection_path = os.path.join(temp_dir, "collection")
        data = [{"id": "user/1", "name": "Alice"}]
        data_lookup = {item["id"]: item for item in data}

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: data,
            get_fn=lambda x: data_lookup.get(x),
        )

        # Get metadata after refresh
        collection.all()
        meta = collection._get_meta()

        # id_map should contain the sanitization mapping
        assert "id_map" in meta
        assert "user/1" in meta["id_map"]

        collection.clear()


class TestFileCollectionCustomIDExtractor:
    """Test custom ID extractor functionality."""

    def test_custom_id_extractor(self, temp_dir):
        """Test using a custom ID extractor."""
        collection_path = os.path.join(temp_dir, "collection")
        data = [
            {"uuid": "abc123", "name": "Alice"},
            {"uuid": "def456", "name": "Bob"},
        ]
        data_lookup = {item["uuid"]: item for item in data}

        def get_uuid(obj):
            return obj["uuid"]

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: data,
            get_fn=lambda x: data_lookup.get(x),
            id_extractor=get_uuid,
        )

        # Should use uuid as ID
        result = collection.get("abc123")
        assert result == data[0]

        assert "abc123" in collection
        assert "def456" in collection

        collection.clear()

    def test_default_id_extractor(self, temp_dir):
        """Test default ID extraction from 'id' field."""
        collection_path = os.path.join(temp_dir, "collection")
        data = [
            {"id": "item1", "value": "data1"},
            {"id": "item2", "value": "data2"},
        ]
        data_lookup = {item["id"]: item for item in data}

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: data,
            get_fn=lambda x: data_lookup.get(x),
            # id_extractor=None  # Default
        )

        result = collection.get("item1")
        assert result == data[0]

        collection.clear()


class TestFileCollectionThreadSafety:
    """Test thread safety of FileCollection."""

    def test_thread_safe_concurrent_gets(self, temp_dir, sample_data):
        """Test that concurrent gets are thread-safe."""
        collection_path = os.path.join(temp_dir, "collection")
        data_lookup = {item["id"]: item for item in sample_data}

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: data_lookup.get(x),
            lru_capacity=10,
        )

        results = []

        def get_item(item_id):
            result = collection.get(item_id)
            results.append(result)

        # Create multiple threads
        threads = []
        for _ in range(5):
            for item_id in ["user1", "user2", "user3"]:
                t = threading.Thread(target=get_item, args=(item_id,))
                threads.append(t)
                t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All results should be valid
        assert len(results) == 15
        assert all(r is not None for r in results)

        collection.clear()

    def test_thread_safe_concurrent_all(self, temp_dir, sample_data):
        """Test that concurrent all() calls are thread-safe."""
        collection_path = os.path.join(temp_dir, "collection")

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: None,
            ttl_list="10m",  # Long TTL so cache is used
        )

        results = []

        def get_all():
            result = collection.all()
            results.append(result)

        # Create multiple threads
        threads = []
        for _ in range(10):
            t = threading.Thread(target=get_all)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All results should be identical
        assert len(results) == 10
        assert all(r == sample_data for r in results)

        collection.clear()


class TestFileCollectionPersistence:
    """Test persistence of data to disk."""

    def test_data_persists_to_disk(self, temp_dir, sample_data):
        """Test that data is saved to disk."""
        collection_path = os.path.join(temp_dir, "collection")

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: None,
        )

        collection.all()

        # Check that .meta file exists
        assert os.path.exists(os.path.join(collection_path, ".meta"))

        # Check that item files were created
        files = [f for f in os.listdir(collection_path) if f.endswith(".json")]
        assert len(files) == 3

        collection.clear()

    def test_data_loaded_from_disk(self, temp_dir, sample_data):
        """Test that data can be loaded from disk cache."""
        collection_path = os.path.join(temp_dir, "collection")

        # Create and populate first collection
        collection1 = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: None,
            ttl_list="1h",
        )

        collection1.all()

        # Create second collection with different list_fn that would fail
        def failing_list_fn():
            raise AssertionError("Should use cache")

        collection2 = FileCollection(
            base_path=collection_path,
            list_fn=failing_list_fn,
            get_fn=lambda x: None,
            ttl_list="1h",
        )

        # Should use cached data, not call failing_list_fn
        result = collection2.all()
        assert result == sample_data

        collection2.clear()

    def test_metadata_persists(self, temp_dir, sample_data):
        """Test that metadata is correctly persisted."""
        collection_path = os.path.join(temp_dir, "collection")

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: None,
        )

        collection.all()

        # Read metadata file directly
        meta_file = os.path.join(collection_path, ".meta")
        with open(meta_file) as f:
            meta = json.load(f)

        assert "list_time" in meta
        assert "items" in meta
        assert "id_map" in meta
        assert len(meta["items"]) == 3

        collection.clear()


class TestFileCollectionRemoval:
    """Test item removal functionality."""

    def test_remove_excessive_items(self, temp_dir):
        """Test that items not in collection are removed from disk."""
        collection_path = os.path.join(temp_dir, "collection")

        # Initial data with 3 items
        initial_data = [
            {"id": "user1", "name": "Alice"},
            {"id": "user2", "name": "Bob"},
            {"id": "user3", "name": "Charlie"},
        ]
        data_lookup = {item["id"]: item for item in initial_data}

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: initial_data,
            get_fn=lambda x: data_lookup.get(x),
        )

        # First refresh creates 3 items
        collection.all()
        files_after_first = len([f for f in os.listdir(collection_path) if f.endswith(".json")])
        assert files_after_first == 3

        # Update list_fn to return only 2 items
        updated_data = [initial_data[0], initial_data[1]]
        collection.list_fn = lambda: updated_data

        # Refresh should remove user3
        collection.all(refresh=True)
        files_after_update = len([f for f in os.listdir(collection_path) if f.endswith(".json")])
        assert files_after_update == 2

        collection.clear()

    def test_clear_removes_all_files(self, temp_dir, sample_data):
        """Test that clear() removes all files."""
        collection_path = os.path.join(temp_dir, "collection")

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: None,
        )

        collection.all()
        assert os.path.exists(collection_path)

        collection.clear()
        assert not os.path.exists(collection_path)


class TestFileCollectionEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_collection_operations(self, temp_dir):
        """Test operations on an empty collection."""
        collection_path = os.path.join(temp_dir, "collection")

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: [],
            get_fn=lambda x: None,
        )

        assert len(collection) == 0
        assert collection.keys() == []
        assert collection.values() == []
        assert collection.items() == []
        assert "anything" not in collection

        collection.clear()

    def test_large_collection(self, temp_dir):
        """Test handling of a large collection."""
        collection_path = os.path.join(temp_dir, "collection")

        # Create 100 items
        data = [{"id": f"item{i}", "value": i} for i in range(100)]
        data_lookup = {item["id"]: item for item in data}

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: data,
            get_fn=lambda x: data_lookup.get(x),
        )

        result = collection.all()
        assert len(result) == 100
        assert len(collection) == 100

        collection.clear()

    def test_get_item_not_in_list(self, temp_dir):
        """Test getting an item that's not in the list."""
        collection_path = os.path.join(temp_dir, "collection")

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: [],
            get_fn=lambda x: ({"id": x, "value": "special"} if x == "special" else None),
        )

        # Item not in list but available via get_fn
        result = collection.get("special")
        assert result == {"id": "special", "value": "special"}

        collection.clear()

    def test_unicode_ids(self, temp_dir):
        """Test handling of unicode characters in IDs."""
        collection_path = os.path.join(temp_dir, "collection")

        data = [
            {"id": "用户1", "name": "Chinese"},
            {"id": "utilisateur2", "name": "French"},
            {"id": "пользователь3", "name": "Russian"},
        ]
        data_lookup = {item["id"]: item for item in data}

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: data,
            get_fn=lambda x: data_lookup.get(x),
        )

        collection.all()

        # Should be able to retrieve by unicode ID
        assert collection.get("用户1") == data[0]
        assert collection.get("utilisateur2") == data[1]
        assert collection.get("пользователь3") == data[2]

        collection.clear()

    def test_relative_path(self, temp_dir):
        """Test using relative paths for collection."""
        # Save current directory
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            # Use relative path
            collection = FileCollection(
                base_path="./relative_collection",
                list_fn=lambda: [],
                get_fn=lambda x: None,
            )

            assert os.path.exists("./relative_collection")
            collection.clear()
        finally:
            os.chdir(original_cwd)


class TestFileCollectionIdFieldName:
    """Test FileCollection with id_field_name parameter."""

    def test_id_field_name_with_dict(self, temp_dir):
        """Test id_field_name parameter with dictionary objects."""
        collection_path = os.path.join(temp_dir, "collection")

        data = [
            {"uuid": "user1", "name": "Alice"},
            {"uuid": "user2", "name": "Bob"},
            {"uuid": "user3", "name": "Charlie"},
        ]
        data_lookup = {item["uuid"]: item for item in data}

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: data,
            get_fn=lambda x: data_lookup.get(x),
            id_field_name="uuid",
        )

        # Should use "uuid" field as ID instead of "id"
        result = collection.all()
        assert len(result) == 3
        assert result == data

        # Should be able to retrieve by uuid
        assert collection.get("user1") == data[0]
        assert collection.get("user2") == data[1]
        assert "user1" in collection

        collection.clear()

    def test_id_field_name_with_custom_field(self, temp_dir):
        """Test id_field_name with a custom field name."""
        collection_path = os.path.join(temp_dir, "collection")

        data = [
            {"email": "alice@example.com", "name": "Alice"},
            {"email": "bob@example.com", "name": "Bob"},
        ]
        data_lookup = {item["email"]: item for item in data}

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: data,
            get_fn=lambda x: data_lookup.get(x),
            id_field_name="email",
        )

        result = collection.get("alice@example.com")
        assert result == data[0]

        assert len(collection) == 2
        assert collection.keys() == ["alice@example.com", "bob@example.com"]

        collection.clear()

    def test_id_field_name_with_object_attributes(self, temp_dir):
        """Test id_field_name with object attributes."""
        collection_path = os.path.join(temp_dir, "collection")

        class Item:
            def __init__(self, item_id, name):
                self.item_id = item_id
                self.name = name

            def __eq__(self, other):
                return isinstance(other, Item) and self.item_id == other.item_id and self.name == other.name

            def __repr__(self):
                return f"Item(item_id={self.item_id!r}, name={self.name!r})"

        data = [
            Item("obj1", "Alice"),
            Item("obj2", "Bob"),
        ]
        data_lookup = {item.item_id: item for item in data}

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: [{"item_id": item.item_id, "name": item.name} for item in data],
            get_fn=lambda x: (
                {"item_id": data_lookup[x].item_id, "name": data_lookup[x].name} if x in data_lookup else None
            ),
            id_field_name="item_id",
        )

        result = collection.get("obj1")
        assert result["item_id"] == "obj1"
        assert result["name"] == "Alice"

        collection.clear()

    def test_both_id_extractor_and_id_field_name_raises_error(self, temp_dir):
        """Test that specifying both id_extractor and id_field_name raises ValueError."""
        collection_path = os.path.join(temp_dir, "collection")

        with pytest.raises(ValueError, match="Cannot specify both id_extractor and id_field_name"):
            FileCollection(
                base_path=collection_path,
                list_fn=lambda: [],
                get_fn=lambda x: None,
                id_extractor=lambda obj: obj.get("id"),
                id_field_name="uuid",
            )

    def test_id_extractor_takes_precedence_when_both_none(self, temp_dir, sample_data):
        """Test that default behavior uses 'id' field when both parameters are None."""
        collection_path = os.path.join(temp_dir, "collection")
        data_lookup = {item["id"]: item for item in sample_data}

        # Both id_extractor and id_field_name are None (default behavior)
        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: sample_data,
            get_fn=lambda x: data_lookup.get(x),
        )

        result = collection.all()
        assert len(result) == 3
        assert result == sample_data

        assert collection.get("user1") == sample_data[0]
        assert "user1" in collection

        collection.clear()

    def test_id_field_name_with_numeric_field(self, temp_dir):
        """Test id_field_name with numeric field values (should be converted to string)."""
        collection_path = os.path.join(temp_dir, "collection")

        data = [
            {"user_id": 101, "name": "Alice"},
            {"user_id": 102, "name": "Bob"},
        ]
        data_lookup = {str(item["user_id"]): item for item in data}

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: data,
            get_fn=lambda x: data_lookup.get(x),
            id_field_name="user_id",
        )

        # Should convert numeric IDs to strings
        assert collection.get("101") == data[0]
        assert collection.get("102") == data[1]
        assert "101" in collection
        assert len(collection) == 2

        collection.clear()

    def test_id_field_name_with_special_characters(self, temp_dir):
        """Test id_field_name with values containing special characters."""
        collection_path = os.path.join(temp_dir, "collection")

        data = [
            {"code": "user/1", "name": "Alice"},
            {"code": "user\\2", "name": "Bob"},
            {"code": "user:3", "name": "Charlie"},
        ]
        data_lookup = {item["code"]: item for item in data}

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: data,
            get_fn=lambda x: data_lookup.get(x),
            id_field_name="code",
        )

        # Should handle special characters in field values
        assert collection.get("user/1") == data[0]
        assert collection.get("user\\2") == data[1]
        assert collection.get("user:3") == data[2]
        assert len(collection) == 3

        collection.clear()

    def test_id_field_name_consistency(self, temp_dir):
        """Test that id_field_name consistently identifies items across operations."""
        collection_path = os.path.join(temp_dir, "collection")

        data = [
            {"product_id": "prod1", "name": "Product 1", "price": 10},
            {"product_id": "prod2", "name": "Product 2", "price": 20},
        ]
        data_lookup = {item["product_id"]: item for item in data}

        collection = FileCollection(
            base_path=collection_path,
            list_fn=lambda: data,
            get_fn=lambda x: data_lookup.get(x),
            id_field_name="product_id",
        )

        # Test all() retrieves items
        all_items = collection.all()
        assert len(all_items) == 2

        # Test keys() returns correct IDs
        keys = collection.keys()
        assert set(keys) == {"prod1", "prod2"}

        # Test items() correctly pairs IDs with data
        items = collection.items()
        assert len(items) == 2
        assert ("prod1", data[0]) in items
        assert ("prod2", data[1]) in items

        # Test iteration
        iterated_items = list(collection)
        assert iterated_items == data

        collection.clear()
