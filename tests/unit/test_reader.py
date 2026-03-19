import os
import unittest

from core.dmconverter.reader import read_records


# テスト用DMファイルのパス
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SAMPLE_DM_FILES = [
    os.path.join(DATA_DIR, "02JF613.dm"),
    os.path.join(DATA_DIR, "02JF711.dm"),
]


class TestReadRecords(unittest.TestCase):
    def test_returns_records(self):
        """DMファイルからレコードが読み取れること"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                records = list(read_records(dm_path))
                self.assertGreater(len(records), 0)

    def test_first_record_is_not_empty(self):
        """先頭レコードが空でないこと"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                records = list(read_records(dm_path))
                self.assertGreater(len(records[0]), 0)

    def test_empty_lines_are_skipped(self):
        """空行がレコードとして返されないこと"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                for record in read_records(dm_path):
                    self.assertGreater(len(record), 0)

    def test_no_newlines_in_records(self):
        """レコードに改行文字が含まれないこと"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                for record in read_records(dm_path):
                    self.assertNotIn("\n", record)
                    self.assertNotIn("\r", record)

    def test_contains_h_records(self):
        """グループヘッダレコード(H)が含まれること"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                records = list(read_records(dm_path))
                h_records = [r for r in records if r.startswith("H ")]
                self.assertGreater(len(h_records), 0)

    def test_file_not_found(self):
        """存在しないファイルでFileNotFoundErrorが発生すること"""
        with self.assertRaises(FileNotFoundError):
            list(read_records("/nonexistent/path.dm"))


if __name__ == "__main__":
    unittest.main()
