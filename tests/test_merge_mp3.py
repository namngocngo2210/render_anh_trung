import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import merge_mp3


class TestNaturalKey(unittest.TestCase):
    def test_numeric_order(self):
        names = ["10.mp3", "2.mp3", "1.mp3"]
        names.sort(key=merge_mp3.natural_key)
        self.assertEqual(names, ["1.mp3", "2.mp3", "10.mp3"])

    def test_mixed_names(self):
        names = ["track10.mp3", "track2.mp3", "Track1.mp3"]
        names.sort(key=merge_mp3.natural_key)
        self.assertEqual(names, ["Track1.mp3", "track2.mp3", "track10.mp3"])


class TestListMp3Files(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        for name in ["3.mp3", "1.mp3", "2.mp3", "note.txt"]:
            (self.folder / name).touch()

    def tearDown(self):
        self.tmp.cleanup()

    def test_sequential_order(self):
        files = merge_mp3.list_mp3_files(self.folder, "sequential")
        self.assertEqual([f.name for f in files], ["1.mp3", "2.mp3", "3.mp3"])

    def test_random_returns_same_files(self):
        files = merge_mp3.list_mp3_files(self.folder, "random")
        self.assertEqual(sorted(f.name for f in files), ["1.mp3", "2.mp3", "3.mp3"])

    def test_excludes_previous_output(self):
        (self.folder / f"{self.folder.name}{merge_mp3.OUTPUT_SUFFIX}").touch()
        files = merge_mp3.list_mp3_files(self.folder, "sequential")
        self.assertEqual([f.name for f in files], ["1.mp3", "2.mp3", "3.mp3"])


class TestWriteConcatList(unittest.TestCase):
    def test_writes_escaped_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            mp3 = folder / "a'b.mp3"
            mp3.touch()
            list_file = folder / "concat_list.txt"
            merge_mp3.write_concat_list([mp3], list_file)
            content = list_file.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("file '"))
            self.assertIn("a'\\''b.mp3", content)
            self.assertNotIn("\\\\", content)


class TestMergeFolderErrors(unittest.TestCase):
    def test_missing_folder(self):
        with self.assertRaises(NotADirectoryError):
            merge_mp3.merge_folder("Z:/khong_ton_tai_123", "sequential")

    def test_empty_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                merge_mp3.merge_folder(tmp, "sequential")


if __name__ == "__main__":
    unittest.main()
