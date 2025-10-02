"""
Tests for the state management module.
"""

import json
import os
import tempfile
import unittest

from yumako.state import StateFile, state_file


class TestStateFile(unittest.TestCase):
    """Test cases for the StateFile class."""

    def setUp(self):
        """Set up a temporary directory for test state files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_path = os.path.join(self.temp_dir.name, "test_state.json")

    def tearDown(self):
        """Clean up temporary files after tests."""
        self.temp_dir.cleanup()

    def test_init_creates_directory(self):
        """Test that initializing a StateFile creates the parent directory if needed."""
        nested_path = os.path.join(self.temp_dir.name, "nested", "dir", "state.json")
        StateFile(nested_path)
        self.assertTrue(os.path.exists(os.path.dirname(nested_path)))

    def test_get_nonexistent_returns_default(self):
        """Test that getting a nonexistent key returns the default value."""
        state = StateFile(self.state_path)
        self.assertIsNone(state.get("nonexistent"))
        self.assertEqual(state.get("nonexistent", "default"), "default")

    def test_set_and_get(self):
        """Test setting and getting values."""
        state = StateFile(self.state_path)
        state.set("key1", "value1")
        state.set("key2", 42)

        self.assertEqual(state.get("key1"), "value1")
        self.assertEqual(state.get("key2"), 42)

    def test_set_creates_file(self):
        """Test that setting a value creates the state file."""
        state = StateFile(self.state_path)
        state.set("key", "value")
        self.assertTrue(os.path.exists(self.state_path))

    def test_file_content(self):
        """Test that the file content is properly formatted JSON."""
        state = StateFile(self.state_path)
        state.set("key1", "value1")
        state.set("key2", 42)

        with open(self.state_path) as f:
            content = json.load(f)

        self.assertEqual(content, {"key1": "value1", "key2": 42})

    def test_reload(self):
        """Test reloading from disk."""
        # Create and populate the state file
        with open(self.state_path, "w") as f:
            json.dump({"key": "original"}, f)

        # Load the state and verify
        state = StateFile(self.state_path)
        self.assertEqual(state.get("key"), "original")

        # Modify the file directly
        with open(self.state_path, "w") as f:
            json.dump({"key": "modified"}, f)

        # Verify reload works
        self.assertEqual(state.get("key", reload=True), "modified")

    def test_unset(self):
        """Test removing a key."""
        state = StateFile(self.state_path)
        state.set("key1", "value1")
        state.set("key2", "value2")

        state.unset("key1")

        self.assertIsNone(state.get("key1"))
        self.assertEqual(state.get("key2"), "value2")

    def test_clear(self):
        """Test clearing all state."""
        state = StateFile(self.state_path)
        state.set("key1", "value1")
        state.set("key2", "value2")

        state.clear()

        self.assertIsNone(state.get("key1"))
        self.assertIsNone(state.get("key2"))
        self.assertTrue(os.path.exists(self.state_path))  # File should still exist

    def test_delete(self):
        """Test deleting the state file."""
        state = StateFile(self.state_path)
        state.set("key", "value")
        self.assertTrue(os.path.exists(self.state_path))

        state.delete()
        self.assertFalse(os.path.exists(self.state_path))

    def test_auto_flush(self):
        """Test auto_flush behavior."""
        # With auto_flush=True (default)
        state1 = StateFile(self.state_path)
        state1.set("key", "value")

        # Create a new instance to verify it's on disk
        state2 = StateFile(self.state_path)
        self.assertEqual(state2.get("key"), "value")

        # With auto_flush=False
        no_flush_path = os.path.join(self.temp_dir.name, "no_flush.json")
        state3 = StateFile(no_flush_path, auto_flush=False)
        state3.set("key", "value")

        # Create a new instance - should not see the change
        state4 = StateFile(no_flush_path)
        self.assertIsNone(state4.get("key"))

        # Flush manually and check again
        state3.flush()
        state5 = StateFile(no_flush_path)
        self.assertEqual(state5.get("key"), "value")

    def test_complex_values(self):
        """Test storing and retrieving complex values."""
        state = StateFile(self.state_path)
        complex_value = {"nested": {"list": [1, 2, 3], "dict": {"a": 1, "b": 2}}, "array": [{"x": 1}, {"y": 2}]}

        state.set("complex", complex_value)
        retrieved = state.get("complex")

        self.assertEqual(retrieved, complex_value)

    def test_dot_property_access_read(self):
        """Test reading values using dot property access."""
        state = StateFile(self.state_path)
        state.set("username", "john_doe")
        state.set("age", 30)
        state.set("is_active", True)

        # Test reading existing properties
        self.assertEqual(state.username, "john_doe")
        self.assertEqual(state.age, 30)
        self.assertEqual(state.is_active, True)

    def test_dot_property_access_write(self):
        """Test writing values using dot property access."""
        state = StateFile(self.state_path)

        # Test setting properties using dot notation
        state.username = "jane_doe"
        state.age = 25
        state.is_active = False
        state.settings = {"theme": "dark", "notifications": True}

        # Verify values were stored correctly
        self.assertEqual(state.get("username"), "jane_doe")
        self.assertEqual(state.get("age"), 25)
        self.assertEqual(state.get("is_active"), False)
        self.assertEqual(state.get("settings"), {"theme": "dark", "notifications": True})

    def test_dot_property_access_nonexistent(self):
        """Test accessing nonexistent properties returns None."""
        state = StateFile(self.state_path)

        # Should return None for nonexistent properties (not raise AttributeError)
        self.assertIsNone(state.nonexistent_property)

    def test_dot_property_access_none_values(self):
        """Test that None values can be accessed via dot notation."""
        state = StateFile(self.state_path)
        state.set("null_value", None)

        # Should be able to access None values
        self.assertIsNone(state.null_value)

    def test_dot_property_access_private_attributes(self):
        """Test that private attributes (starting with _) are handled normally."""
        state = StateFile(self.state_path)

        # Private attributes should not be intercepted by __getattr__
        with self.assertRaises(AttributeError):
            _ = state._private_attr

        # Private attributes should not be intercepted by __setattr__
        state._private_attr = "test"
        self.assertEqual(state._private_attr, "test")

    def test_dot_property_access_with_auto_flush(self):
        """Test that dot property access respects auto_flush setting."""
        # Test with auto_flush=True (default)
        state1 = StateFile(self.state_path)
        state1.username = "test_user"

        # Create a new instance to verify it's persisted
        state2 = StateFile(self.state_path)
        self.assertEqual(state2.username, "test_user")

        # Test with auto_flush=False
        no_flush_path = os.path.join(self.temp_dir.name, "no_flush.json")
        state3 = StateFile(no_flush_path, auto_flush=False)
        state3.username = "no_flush_user"

        # Create a new instance - should not see the change
        state4 = StateFile(no_flush_path)
        self.assertIsNone(state4.username)  # Should return None, not raise AttributeError

        # Flush manually and check again
        state3.flush()
        state5 = StateFile(no_flush_path)
        self.assertEqual(state5.username, "no_flush_user")

    def test_dot_property_access_mixed_with_get_set(self):
        """Test that dot property access works alongside get/set methods."""
        state = StateFile(self.state_path)

        # Set using dot notation
        state.username = "dot_user"

        # Get using traditional method
        self.assertEqual(state.get("username"), "dot_user")

        # Set using traditional method
        state.set("email", "dot@example.com")

        # Get using dot notation
        self.assertEqual(state.email, "dot@example.com")

        # Mix both approaches
        state.set("age", 30)
        state.city = "New York"

        self.assertEqual(state.get("age"), 30)
        self.assertEqual(state.city, "New York")

    def test_discard(self):
        """Test discarding state from memory while keeping file on disk."""
        state = StateFile(self.state_path)
        state.set("key1", "value1")
        state.set("key2", "value2")

        # Verify data is in memory and on disk
        self.assertEqual(state.get("key1"), "value1")
        self.assertTrue(os.path.exists(self.state_path))

        # Discard from memory
        state.discard()

        # Data should be cleared from memory
        self.assertIsNone(state.get("key1"))
        self.assertIsNone(state.get("key2"))

        # But file should still exist on disk
        self.assertTrue(os.path.exists(self.state_path))

        # Verify file content is still there
        with open(self.state_path) as f:
            content = json.load(f)
        self.assertEqual(content, {"key1": "value1", "key2": "value2"})


class TestStateFileFunction(unittest.TestCase):
    """Test cases for the state_file() function singleton behavior."""

    def setUp(self):
        """Set up a temporary directory for test state files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_path = os.path.join(self.temp_dir.name, "test_state.json")

    def tearDown(self):
        """Clean up temporary files after tests."""
        self.temp_dir.cleanup()

    def test_state_file_singleton_behavior(self):
        """Test that state_file() returns the same instance for the same path."""
        state1 = state_file(self.state_path)
        state2 = state_file(self.state_path)

        # Should return the same instance
        self.assertIs(state1, state2)

        # Changes in one should be visible in the other
        state1.set("key", "value")
        self.assertEqual(state2.get("key"), "value")

    def test_state_file_path_normalization(self):
        """Test that state_file() normalizes paths correctly."""
        # Test with relative path
        relative_path = "test.json"
        state1 = state_file(relative_path)

        # Test with absolute path to same file
        abs_path = os.path.abspath(relative_path)
        state2 = state_file(abs_path)

        # Should return the same instance
        self.assertIs(state1, state2)

        # Test with tilde expansion
        home_path = os.path.expanduser("~/test_state.json")
        state3 = state_file(home_path)

        # Should be different from the previous instances
        self.assertIsNot(state1, state3)

    def test_state_file_with_discard(self):
        """Test that discard() removes instance from state_file() cache."""
        state1 = state_file(self.state_path)
        state1.set("key", "value")

        # Discard the state
        state1.discard()

        # Getting a new instance should create a fresh one
        state2 = state_file(self.state_path)
        self.assertIsNot(state1, state2)

        # The new instance should have the data loaded
        self.assertEqual(state2.get("key"), "value")

        # But the file should still exist with the data
        self.assertTrue(os.path.exists(self.state_path))
        with open(self.state_path) as f:
            content = json.load(f)
        self.assertEqual(content, {"key": "value"})

    def test_state_file_thread_safety(self):
        """Test that state_file() function is thread-safe."""
        import threading
        import time

        results = []

        def get_state_file():
            state = state_file(self.state_path)
            results.append(state)
            time.sleep(0.01)  # Small delay to increase chance of race condition

        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_state_file)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All results should be the same instance
        self.assertEqual(len(results), 10)
        first_result = results[0]
        for result in results:
            self.assertIs(result, first_result)


if __name__ == "__main__":
    unittest.main()
