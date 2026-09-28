import os
import tempfile
import unittest

from core.dmconverter.parser.reader import detect_encoding, read_records

# テスト用DMファイル（tests/scripts/generate_test_data.py が生成する合成データ）
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# ファイル名 → detect_encoding の期待値
EXPECTED_ENCODINGS = {
    "synthetic_cs06_1000_cp932.dm": "cp932",
    "synthetic_cs09_1000_utf8_bom.dm": "utf-8",
    "synthetic_cs12_2500_cp932_rev3.dm": "cp932",
    "synthetic_cs08_2500_oldjis.dm": "old_jis",
    "synthetic_cs01_500_utf8_lf.dm": "utf-8",
}
SAMPLE_DM_FILES = [os.path.join(DATA_DIR, name) for name in EXPECTED_ENCODINGS]


def _to_old_jis(text: str) -> bytes:
    """全角文字列を旧型式DMの7bit JIS（EUC-JP の各バイト - 0x80）に符号化する。"""
    return bytes(b - 0x80 for b in text.encode("euc_jp"))


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
                self.assertIn(enc, ("utf-8-sig", "utf-8", "cp932", "old_jis"))

    def test_expected_encoding_per_file(self):
        """合成データ各ファイルが想定どおりのエンコーディングと判定されること"""
        for name, expected in EXPECTED_ENCODINGS.items():
            with self.subTest(name=name):
                enc = detect_encoding(os.path.join(DATA_DIR, name))
                self.assertEqual(enc, expected)

    def test_detect_encoding_old_jis(self):
        """全バイトがASCII範囲のファイルはold_jisと判定されること"""
        content = b"M 08SYN004 " + _to_old_jis("テスト") + b" 2500\r\n"
        with tempfile.NamedTemporaryFile(suffix=".dm", delete=False) as f:
            f.write(content)
            tmp_path = f.name
        try:
            self.assertEqual(detect_encoding(tmp_path), "old_jis")
        finally:
            os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
