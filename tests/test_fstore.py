"""Tests for the directory-backed key-value store."""

import json
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from yumako.fstore import FStore
from yumako.jsondot import DotDict


class TestFStore(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.temp_dir.name, "store")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_ram_roundtrip(self) -> None:
        store = FStore()
        self.assertIsNone(store.get_path("k"))
        self.assertIsNone(store.get("missing"))
        self.assertEqual(store.get("missing", default={"a": 1}), {"a": 1})
        payload = {"n": 1, "child": {"a": 2}}
        store.save("k", payload)
        payload["n"] = 9
        loaded = store.get("k")
        self.assertIsInstance(loaded, DotDict)
        self.assertEqual(loaded, {"n": 1, "child": {"a": 2}})
        self.assertEqual(loaded.child.a, 2)
        self.assertTrue(store.exists("k"))
        self.assertEqual(store.size(), 1)
        store.delete("k")
        self.assertFalse(store.exists("k"))
        self.assertIsNone(store.get("k"))
        self.assertIsNot(FStore(), FStore())

    def test_ram_has_no_children(self) -> None:
        store = FStore()
        with self.assertRaises(ValueError):
            store.child("a")
        with self.assertRaises(ValueError):
            store.children()

    def test_disk_json_roundtrip(self) -> None:
        store = FStore(self.path)
        self.assertEqual(store.get_path("obj"), os.path.join(os.path.realpath(self.path), "obj"))
        store.save("obj", {"a": 1, 2: "x"})
        store.save("nums", (1, 2))
        store.save("text", "hello")
        store.save("empty", None)
        alias = os.path.join(self.path, "..", os.path.basename(self.path))
        again = FStore(alias)
        self.assertIs(again, store)
        self.assertIs(again.get("obj"), store.get("obj"))
        obj = again.get("obj", reload=True)
        self.assertIsInstance(obj, DotDict)
        self.assertEqual(obj, {"a": 1, "2": "x"})
        self.assertEqual(obj.a, 1)
        self.assertEqual(again.get("nums", reload=True), [1, 2])
        self.assertEqual(again.get("text"), "hello")
        self.assertIsNone(again.get("empty", default="fallback"))
        self.assertEqual(again.get("missing", default="fallback"), "fallback")
        with open(os.path.join(self.path, "text"), encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), "hello")

    def test_text_format(self) -> None:
        store = FStore(self.path)
        store.save("note.txt", "raw")
        store.save("other", "raw", format="text")
        self.assertEqual(store.get("note.txt"), "raw")
        self.assertEqual(store.get("other", format="text"), "raw")
        with open(os.path.join(self.path, "other"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "raw")
        with self.assertRaises(ValueError):
            store.save("other", {"a": 1}, format="text")

    def test_json_extension_probe(self) -> None:
        os.makedirs(self.path)
        with open(os.path.join(self.path, "item.json"), "w", encoding="utf-8") as handle:
            json.dump({"ok": True}, handle)
        self.assertEqual(FStore(self.path).get("item"), {"ok": True})

    def test_invalid_key_and_format(self) -> None:
        store = FStore(self.path)
        for key in ("", ".", "..", "a/b", "a\\b"):
            with self.assertRaises(ValueError):
                store.save(key, {})
        with self.assertRaises(ValueError):
            store.save("k", {}, format="xml")

    def test_create_false_and_file_path(self) -> None:
        missing = os.path.join(self.temp_dir.name, "missing")
        with self.assertRaises(ValueError):
            FStore(missing, create=False).save("k", {})
        file_path = os.path.join(self.temp_dir.name, "file")
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write("x")
        with self.assertRaises(ValueError):
            FStore(file_path).save("k", {})

    def test_children_patch_and_doc(self) -> None:
        store = FStore(self.path)
        store.child("a").child("b").save("k", {"n": 1})
        store.child("c").save("k", {"n": 2})
        self.assertEqual(sorted(store.children()), ["a", "c"])
        self.assertEqual(sorted(store.children(depth=1)), ["a", os.path.join("a", "b"), "c"])
        self.assertEqual(store.patch("doc", {"a": 1}), {"a": 1})
        self.assertEqual(store.patch("doc", {"b": 2}), {"a": 1, "b": 2})
        with store.doc("doc") as doc:
            doc["c"] = 3
        self.assertEqual(store.get("doc"), {"a": 1, "b": 2, "c": 3})
        with self.assertRaises(RuntimeError):
            with store.doc("nope") as doc:
                doc["a"] = 1
                raise RuntimeError("nope")
        self.assertIsNone(store.get("nope"))

    def test_keys_drop_missing_and_track_unloaded(self) -> None:
        store = FStore(self.path)
        store.save("k", {"n": 1})
        os.remove(os.path.join(self.path, "k"))
        with open(os.path.join(self.path, "new"), "w", encoding="utf-8") as handle:
            json.dump({"n": 2}, handle)
        self.assertFalse(store.contains("k"))
        self.assertFalse(store.exists("k"))
        self.assertEqual(store._unloaded_keys(), ["new"])
        self.assertTrue(store.contains("new"))
        self.assertEqual(store.get("new"), {"n": 2})
        self.assertEqual(store._unloaded_keys(), [])
        self.assertIsNone(store.get("k"))

    def test_dict_operators(self) -> None:
        store = FStore(self.path)
        self.assertFalse(store)
        self.assertEqual(len(store), 0)
        self.assertNotIn("k", store)
        self.assertNotIn(1, store)
        self.assertNotIn("a/b", store)
        store["k"] = {"n": 1}
        store["empty"] = None
        self.assertTrue(store)
        self.assertEqual(len(store), 2)
        self.assertIn("k", store)
        self.assertEqual(store["k"], {"n": 1})
        self.assertIsNone(store["empty"])
        self.assertEqual(sorted(store), sorted(store.keys()))
        with self.assertRaises(KeyError):
            store["missing"]
        with self.assertRaises(KeyError):
            del store["missing"]
        with self.assertRaises(TypeError):
            store[1] = {}
        del store["k"]
        self.assertNotIn("k", store)
        self.assertEqual(len(store), 1)
        self.assertFalse(os.path.isfile(os.path.join(self.path, "k")))
        with self.assertRaises(TypeError):
            store[1]
        with self.assertRaises(TypeError):
            del store[1]

    def test_ram_operators(self) -> None:
        store = FStore()
        self.assertFalse(store)
        self.assertEqual(store._unloaded_keys(), [])
        store.get("missing", default={"a": 1})
        self.assertNotIn("missing", store)
        store["k"] = {"n": 1}
        self.assertEqual(list(store), ["k"])
        self.assertEqual(store["k"].n, 1)
        store.delete("missing")
        self.assertEqual(len(store), 1)
        del store["k"]
        self.assertFalse(store)

    def test_first_create_flag_sticks(self) -> None:
        store = FStore(self.path, create=False)
        again = FStore(self.path)
        self.assertIs(again, store)
        with self.assertRaises(ValueError):
            again.save("k", {})

    def test_external_file_matches_len_and_iter(self) -> None:
        os.makedirs(self.path)
        with open(os.path.join(self.path, "new"), "w", encoding="utf-8") as handle:
            json.dump({"n": 2}, handle)
        store = FStore(self.path)
        self.assertEqual(list(store), ["new"])
        self.assertEqual(len(store), 1)
        self.assertIn("new", store)
        self.assertEqual(store.values(), [{"n": 2}])
        self.assertEqual(store["new"], {"n": 2})
        os.remove(os.path.join(self.path, "new"))
        self.assertNotIn("new", store)
        self.assertEqual(len(store), 0)
        self.assertEqual(list(store), [])

    def test_clear_keeps_directory(self) -> None:
        store = FStore(self.path)
        store.save("a", 1)
        store.save("b", 2)
        store.clear()
        self.assertEqual(store.keys(), [])
        self.assertFalse(store)
        self.assertTrue(os.path.isdir(self.path))
        self.assertFalse(os.path.isfile(os.path.join(self.path, "a")))

    def test_children_edges(self) -> None:
        store = FStore(self.path)
        self.assertEqual(store.children(), [])
        store.child("a").child("b").child("c").save("k", 1)
        self.assertIs(store.child("a"), store.child("a"))
        nested = ["a", os.path.join("a", "b"), os.path.join("a", "b", "c")]
        self.assertEqual(sorted(store.children(depth=-1)), nested)
        with self.assertRaises(ValueError):
            store.children(-2)

    def test_patch_and_doc_from_missing(self) -> None:
        store = FStore(self.path)
        self.assertEqual(store.patch("p", {"a": 1}), {"a": 1})
        with store.doc("fresh") as doc:
            self.assertEqual(dict(doc), {})
            doc["a"] = 1
        self.assertEqual(store["fresh"], {"a": 1})

    def test_invalid_json(self) -> None:
        os.makedirs(self.path)
        with open(os.path.join(self.path, "k"), "w", encoding="utf-8") as handle:
            handle.write("{")
        with self.assertRaises(ValueError):
            FStore(self.path).get("k")

    def test_reload_clear_destroy(self) -> None:
        store = FStore(self.path)
        store.save("k", {"n": 1})
        with open(os.path.join(self.path, "k"), "w", encoding="utf-8") as handle:
            json.dump({"n": 2}, handle)
        self.assertEqual(store.get("k"), {"n": 1})
        self.assertEqual(store.get("k", reload=True), {"n": 2})
        self.assertEqual(store.items(), [("k", {"n": 2})])
        self.assertEqual(store.values(), [{"n": 2}])
        store.clear()
        self.assertEqual(store.keys(), [])
        store.save("k", {"n": 3})
        store.destroy()
        self.assertFalse(os.path.exists(self.path))
        store.save("k", {"n": 4})
        self.assertEqual(FStore(self.path).get("k"), {"n": 4})

    def test_compact_and_not_object(self) -> None:
        store = FStore(self.path)
        store.save("k", [1], format="json-compact")
        with open(os.path.join(self.path, "k"), encoding="utf-8") as handle:
            self.assertNotIn("\n", handle.read())
        with self.assertRaises(ValueError):
            store.patch("k", {"a": 1})
        with self.assertRaises(ValueError):
            store.doc("k")
        with self.assertRaises(ValueError):
            store.save("k", object())

    def test_yaml_roundtrip_uses_pyyaml(self) -> None:
        module = types.ModuleType("yaml")

        def safe_dump(data: object, **_kwargs: object) -> str:
            return json.dumps(data)

        def safe_load(text: str) -> object:
            return json.loads(text)

        module.safe_dump = safe_dump  # type: ignore[attr-defined]
        module.safe_load = safe_load  # type: ignore[attr-defined]
        store = FStore(self.path)
        with patch.dict(sys.modules, {"yaml": module}):
            store.save("doc.yml", {"a": 1})
            store.save("other", {"b": 2}, format="yaml")
            doc = store.get("doc.yml")
            self.assertIsInstance(doc, DotDict)
            self.assertEqual(doc.a, 1)
            other = FStore(self.path).get("other", format="yml")
            self.assertIsInstance(other, DotDict)
            self.assertEqual(other.b, 2)
        with open(os.path.join(self.path, "doc.yml"), encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), {"a": 1})

    def test_yaml_missing_and_json_skips_it(self) -> None:
        store = FStore(self.path)
        with patch.dict(sys.modules, {"yaml": None}):
            store.save("k", {"a": 1})
            self.assertEqual(store.get("k"), {"a": 1})
            with self.assertRaises(ImportError) as caught:
                store.save("doc.yaml", {"a": 1})
            self.assertIn("PyYAML", str(caught.exception))
            with self.assertRaises(ImportError):
                store.save("k", {"a": 1}, format="yml")

    def test_patch_holds_store_lock(self) -> None:
        store = FStore(self.path)
        owned: list[bool] = []
        real_save = store.save

        def wrapped(key: str, data: object, format: str = "auto") -> object:
            owned.append(store._lock._is_owned())
            return real_save(key, data, format=format)

        store.save = wrapped  # type: ignore[method-assign]
        store.patch("k", {"a": 1})
        self.assertEqual(owned, [True])
