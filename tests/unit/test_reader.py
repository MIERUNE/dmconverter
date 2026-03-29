import os
import unittest

from core.dmconverter.reader import detect_encoding, read_records

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
                    self.assertNotIn(b"\n", record)
                    self.assertNotIn(b"\r", record)

    def test_contains_h_records(self):
        """グループヘッダレコード(H)が含まれること"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                records = list(read_records(dm_path))
                h_records = [r for r in records if r.startswith(b"H ")]
                self.assertGreater(len(h_records), 0)

    def test_returns_bytes(self):
        """レコードがbytes型で返されること"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                records = list(read_records(dm_path))
                for record in records:
                    self.assertIsInstance(record, bytes)

    def test_records_are_84_bytes(self):
        """全レコードが84バイトであること"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                for record in read_records(dm_path):
                    self.assertEqual(len(record), 84)

    def test_file_not_found(self):
        """存在しないファイルでFileNotFoundErrorが発生すること"""
        with self.assertRaises(FileNotFoundError):
            list(read_records("/nonexistent/path.dm"))

    def test_detect_encoding_returns_str(self):
        """detect_encodingがエンコーディング文字列を返すこと"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                enc = detect_encoding(dm_path)
                self.assertIsInstance(enc, str)
                self.assertIn(enc, ("utf-8-sig", "utf-8", "cp932"))


if __name__ == "__main__":
    unittest.main()
