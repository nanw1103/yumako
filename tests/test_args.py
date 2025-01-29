import sys
from unittest import TestCase, main

from yumako.args import _Args


class TestArgs(TestCase):
    def setUp(self):
        # Save original argv
        self.original_argv = sys.argv
        sys.argv = ["script.py"]  # Reset argv to just the script name

    def tearDown(self):
        # Restore original argv
        sys.argv = self.original_argv

    def test_empty_args(self):
        args = _Args()
        self.assertEqual(len(args), 0)
        self.assertEqual(list(args), [])

    def test_key_value_args(self):
        sys.argv = ["script.py", "foo=bar", "debug=true"]
        args = _Args()
        self.assertEqual(args["foo"], "bar")
        self.assertEqual(args["debug"], "true")

    def test_flag_args(self):
        sys.argv = ["script.py", "verbose", "debug"]
        args = _Args()
        self.assertEqual(args["verbose"], "true")
        self.assertEqual(args["debug"], "true")

    def test_mixed_args(self):
        sys.argv = ["script.py", "foo=bar", "verbose"]
        args = _Args()
        self.assertEqual(args["foo"], "bar")
        self.assertEqual(args["verbose"], "true")

    def test_case_insensitive(self):
        sys.argv = ["script.py", "FOO=bar"]
        args = _Args()
        self.assertEqual(args["foo"], "bar")
        self.assertEqual(args["FOO"], "bar")
        self.assertEqual(args["Foo"], "bar")

    def test_snake_camel_case(self):
        sys.argv = ["script.py", "foo_bar=value"]
        args = _Args()
        self.assertEqual(args["foo_bar"], "value")
        self.assertEqual(args["fooBar"], "value")

    def test_bool_conversion(self):
        sys.argv = [
            "script.py",
            "debug=true",
            "verbose=1",
            "quiet=false",
            "test=yes",
            "k1=on",
            "k2=off",
            "k3=1",
            "k4=t",
            "k5=yes",
            "k6=y",
            "k7=YES",
            "k8=Y",
            "k9=no",
        ]
        args = _Args()
        self.assertTrue(args.bool("debug"))
        self.assertTrue(args.bool("verbose"))
        self.assertFalse(args.bool("quiet"))
        self.assertTrue(args.bool("test"))
        self.assertFalse(args.bool("nonexistent"))
        self.assertTrue(args.bool("k1"))
        self.assertFalse(args.bool("k2"))
        self.assertTrue(args.bool("k3"))
        self.assertTrue(args.bool("k4"))
        self.assertTrue(args.bool("k5"))
        self.assertTrue(args.bool("k6"))
        self.assertTrue(args.bool("k7"))
        self.assertTrue(args.bool("k8"))
        self.assertFalse(args.bool("k9"))

    def test_int_conversion(self):
        sys.argv = ["script.py", "count=42", "zero=0"]
        args = _Args()
        self.assertEqual(args.int("count"), 42)
        self.assertEqual(args.int("zero"), 0)
        self.assertEqual(args.int("nonexistent"), 0)  # default value

    def test_duplicate_keys(self):
        sys.argv = ["script.py", "foo=1", "foo=2"]
        with self.assertRaises(ValueError):
            _Args().get("foo")

    def test_get_default(self):
        sys.argv = ["script.py", "foo=bar"]
        args = _Args()
        self.assertEqual(args.get("foo"), "bar")
        self.assertIsNone(args.get("nonexistent"))
        self.assertEqual(args.get("nonexistent", "default"), "default")


if __name__ == "__main__":
    main()
