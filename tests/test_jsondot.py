"""Tests for dot-access dicts and JSON load/save."""

import copy
import os
import tempfile
import unittest
from typing import IO, Any

from yumako.jsondot import DotDict, dotify, load, parse, plain, save, undot


class TestJsonDot(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_attributes(self) -> None:
        data = DotDict({"a": 1, "b": {"c": 2}})
        nested = dotify(data)
        self.assertEqual(nested.a, 1)
        self.assertEqual(nested.b.c, 2)
        nested.b.c = 3
        self.assertEqual(nested["b"]["c"], 3)
        self.assertIsNone(nested.missing)
        self.assertEqual(nested, {"a": 1, "b": {"c": 3}})

    def test_undot_and_plain(self) -> None:
        dotted = dotify({"a": [{"b": 1}]})
        self.assertIsInstance(dotted.a[0], DotDict)
        self.assertEqual(undot(dotted), {"a": [{"b": 1}]})
        self.assertNotIsInstance(undot(dotted)["a"][0], DotDict)
        self.assertEqual(plain(dotted), {"a": [{"b": 1}]})
        self.assertEqual(plain("x"), "x")

    def test_parse_and_cycle(self) -> None:
        parsed = parse('{"hello": {"message": "hi"}}')
        self.assertEqual(parsed.hello.message, "hi")
        with self.assertRaises(ValueError):
            parse("{")
        with self.assertRaises(TypeError):
            parse(1)  # type: ignore[arg-type]
        loop: dict[str, Any] = {}
        loop["self"] = loop
        with self.assertRaises(RecursionError):
            dotify(loop)

    def test_load_and_save(self) -> None:
        path = os.path.join(self.temp_dir.name, "nested", "data.json")
        save({"hello": {"message": "hi"}}, path)
        loaded = load(path)
        self.assertEqual(loaded.hello.message, "hi")
        with open(path, encoding="utf-8") as handle:
            self.assertIn("\n", handle.read())
        compact = os.path.join(self.temp_dir.name, "compact.json")
        save({"n": 1}, compact, pretty=False)
        with open(compact, encoding="utf-8") as handle:
            self.assertNotIn("\n", handle.read())
        missing = os.path.join(self.temp_dir.name, "missing.json")
        self.assertEqual(load(missing, default={"a": 1}).a, 1)
        with self.assertRaises(ValueError):
            load(missing)
        with open(compact, "w", encoding="utf-8") as handle:
            handle.write("{")
        with self.assertRaises(ValueError):
            load(compact)

    def test_lock_is_optional(self) -> None:
        path = os.path.join(self.temp_dir.name, "locked.json")
        calls: list[tuple[str, bool]] = []

        def lock_file(file: IO[str], for_read: bool) -> None:
            calls.append((os.path.basename(file.name), for_read))

        save({"n": 1}, path)
        load(path)
        self.assertEqual(calls, [])

        save({"n": 2}, path, lock=lock_file)
        self.assertEqual(load(path, lock=lock_file).n, 2)
        self.assertEqual(calls, [("locked.json", False), ("locked.json", True)])

        save({"n": 3}, path)
        self.assertEqual(calls, [("locked.json", False), ("locked.json", True)])

    def test_set_delete_eq_and_copy(self) -> None:
        data = DotDict({"a": 1})
        data.b = {"c": 2}
        self.assertEqual(data["b"], {"c": 2})
        del data.a
        self.assertIsNone(data.a)
        self.assertNotIn("a", data)
        with self.assertRaises(KeyError):
            del data.missing
        self.assertNotEqual(data, 1)

        original = dotify({"a": {"b": [1]}})
        copied = copy.deepcopy(original)
        copied.a.b.append(2)
        self.assertEqual(original.a.b, [1])
        self.assertIsInstance(copied.a, DotDict)
        self.assertIsInstance(copied.a.b, list)

    def test_parse_shapes(self) -> None:
        self.assertIsNone(parse("null"))
        parsed = parse('[1, {"a": {"b": 2}}]')
        self.assertEqual(parsed[0], 1)
        self.assertIsInstance(parsed[1], DotDict)
        self.assertEqual(parsed[1].a.b, 2)
        self.assertIsNone(dotify(None))
        self.assertEqual(undot(1), 1)
        self.assertEqual(plain(None), None)

    def test_plain_object_and_save(self) -> None:
        class Box:
            def __init__(self) -> None:
                self.n = 1

        box = Box()
        self.assertIs(plain(box), box)
        path = os.path.join(self.temp_dir.name, "box.json")
        save(box, path, pretty=False)
        self.assertEqual(load(path), {"n": 1})
        with self.assertRaises(ValueError):
            save({1, 2}, os.path.join(self.temp_dir.name, "bad.json"))

    def test_load_default_is_dotified(self) -> None:
        missing = os.path.join(self.temp_dir.name, "missing.json")
        default = {"a": {"b": 1}}
        loaded = load(missing, default=default)
        self.assertIsInstance(loaded, DotDict)
        self.assertIsInstance(loaded.a, DotDict)
        loaded.a.b = 9
        self.assertEqual(default["a"]["b"], 1)
        path = os.path.join(self.temp_dir.name, "pretty.json")
        save({"a": 1}, path)
        with open(path, encoding="utf-8") as handle:
            self.assertIn("\n    ", handle.read())
