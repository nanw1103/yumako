import os
from unittest import TestCase, main

from yumako.env import _Env


class TestEnv(TestCase):
    def setUp(self):
        # Save original environment
        self.original_env = dict(os.environ)
        # Clear environment for testing
        os.environ.clear()

    def tearDown(self):
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_empty_env(self):
        env = _Env()
        self.assertEqual(len(env), 0)
        self.assertEqual(list(env), [])

    def test_get_set(self):
        env = _Env()
        env["TEST"] = "value"
        self.assertEqual(env["TEST"], "value")
        self.assertEqual(os.environ["TEST"], "value")

    def test_delete(self):
        env = _Env()
        env["TEST"] = "value"
        del env["TEST"]
        with self.assertRaises(KeyError):
            _ = env["TEST"]
        self.assertNotIn("TEST", os.environ)

    def test_case_insensitive(self):
        env = _Env()
        env["TEST"] = "value"
        self.assertEqual(env["test"], "value")
        self.assertEqual(env["Test"], "value")
        self.assertEqual(env["TEST"], "value")

    def test_bool_conversion(self):
        env = _Env()
        test_values = {
            "true": True,
            "True": True,
            "t": True,
            "yes": True,
            "y": True,
            "1": True,
            "on": True,
            "enabled": True,
            "false": False,
            "False": False,
            "f": False,
            "no": False,
            "n": False,
            "0": False,
            "off": False,
            "disabled": False,
        }
        for value, expected in test_values.items():
            env["TEST"] = value
            self.assertEqual(env.bool("TEST"), expected)

    def test_bool_default(self):
        env = _Env()
        self.assertFalse(env.bool("NONEXISTENT"))
        self.assertTrue(env.bool("NONEXISTENT", default=True))

    def test_int_conversion(self):
        env = _Env()
        env["TEST"] = "42"
        self.assertEqual(env.int("TEST"), 42)
        env["TEST"] = "-42"
        self.assertEqual(env.int("TEST"), -42)
        env["TEST"] = "0"
        self.assertEqual(env.int("TEST"), 0)

    def test_int_default(self):
        env = _Env()
        self.assertEqual(env.int("NONEXISTENT"), 0)
        self.assertEqual(env.int("NONEXISTENT", default=42), 42)

    def test_int_invalid(self):
        env = _Env()
        env["TEST"] = "not a number"
        with self.assertRaises(ValueError):
            env.int("TEST")

    def test_case_insensitive_delete(self):
        env = _Env()
        env["TEST"] = "value"
        del env["test"]
        self.assertNotIn("TEST", env)
        self.assertNotIn("TEST", os.environ)

    def test_iteration(self):
        env = _Env()
        test_data = {"TEST1": "value1", "TEST2": "value2", "TEST3": "value3"}
        for k, v in test_data.items():
            env[k] = v
        self.assertEqual(set(env), set(test_data.keys()))


if __name__ == "__main__":
    main()
