"""
Tests for the state management module.
"""

import json
import os
import tempfile
import unittest

from yumako.state import StateFile, default_state, init_default


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


class TestDefaultState(unittest.TestCase):
    """Test cases for the default state file functionality."""

    def setUp(self):
        """Set up a temporary directory for test state files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_path = os.path.join(self.temp_dir.name, "default_state.json")

        # Reset the module-level default state
        import yumako.state

        yumako.state._default = None

    def tearDown(self):
        """Clean up temporary files after tests."""
        self.temp_dir.cleanup()

        # Reset the module-level default state
        import yumako.state

        yumako.state._default = None

    def test_init_default(self):
        """Test initializing the default state file."""
        state = init_default(self.state_path)
        self.assertEqual(state._path, self.state_path)

    def test_default_state(self):
        """Test getting the default state file."""
        # Should create with default path
        state1 = default_state()
        self.assertEqual(state1._path, ".state")

        # Should return the same instance
        state2 = default_state()
        self.assertIs(state1, state2)

    def test_init_default_twice(self):
        """Test that initializing default twice with different paths raises an error."""
        init_default(self.state_path)

        with self.assertRaises(ValueError):
            init_default(os.path.join(self.temp_dir.name, "other_path.json"))

    def test_init_default_twice_same_path(self):
        """Test that initializing default twice with the same path works."""
        state1 = init_default(self.state_path)
        state2 = init_default(self.state_path)
        self.assertIs(state1, state2)


if __name__ == "__main__":
    unittest.main()
