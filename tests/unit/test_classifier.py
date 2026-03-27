import os
import unittest

from core.dmconverter.classifier import (
    ClassifiedRecords,
    _has_following_lines,
    _is_element_prefix,
    _is_header_prefix,
    _is_modification_history,
    _is_skip_prefix,
    classify,
)
from core.dmconverter.reader import read_records

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SAMPLE_DM_FILES = [
    os.path.join(DATA_DIR, "02JF613.dm"),
    os.path.join(DATA_DIR, "02JF711.dm"),
]


class TestIsModificationHistory(unittest.TestCase):
    def test_position_79_digit_returns_true(self):
        """位置79が"1"-"9"なら修正履歴"""
        record = b" " * 79 + b"1"
        self.assertTrue(_is_modification_history(record))

    def test_position_79_space_returns_false(self):
        """位置79がスペースなら修正履歴でない"""
        record = b" " * 79 + b" "
        self.assertFalse(_is_modification_history(record))

    def test_position_79_zero_returns_false(self):
        """位置79が"0"なら修正履歴でない"""
        record = b" " * 79 + b"0"
        self.assertFalse(_is_modification_history(record))

    def test_short_record_returns_false(self):
        """80文字未満のレコードは修正履歴でない"""
        record = b" " * 50
        self.assertFalse(_is_modification_history(record))


class TestIsElementPrefix(unittest.TestCase):
    def test_e1_to_e8(self):
        """E1-E8を正しく判定する"""
        for i in range(1, 9):
            with self.subTest(i=i):
                self.assertTrue(_is_element_prefix(f"E{i}2101".encode()))

    def test_e0_returns_false(self):
        """E0は要素レコードでない"""
        self.assertFalse(_is_element_prefix(b"E02101"))

    def test_e9_returns_false(self):
        """E9は要素レコードでない"""
        self.assertFalse(_is_element_prefix(b"E92101"))

    def test_short_string_returns_false(self):
        """1文字のレコードは要素レコードでない"""
        self.assertFalse(_is_element_prefix(b"E"))


class TestIsHeaderPrefix(unittest.TestCase):
    def test_header_record(self):
        self.assertTrue(_is_header_prefix(b"H 2100"))

    def test_non_header(self):
        self.assertFalse(_is_header_prefix(b"E22101"))


class TestIsSkipPrefix(unittest.TestCase):
    def test_grid_record(self):
        self.assertTrue(_is_skip_prefix(b"G 0001"))

    def test_tin_record(self):
        self.assertTrue(_is_skip_prefix(b"T 0001"))

    def test_non_skip(self):
        self.assertFalse(_is_skip_prefix(b"H 2100"))


class TestHasFollowingLines(unittest.TestCase):
    def test_e1_to_e4_have_following_lines(self):
        """E1-E4は後続の座標行を持つ"""
        for t in b"1234":
            with self.subTest(t=t):
                self.assertTrue(_has_following_lines(t))

    def test_e5_has_no_following_lines(self):
        """E5は座標がE行に埋め込まれているため後続行なし"""
        self.assertFalse(_has_following_lines(ord(b"5")))

    def test_e6_to_e8_have_following_lines(self):
        """E6は座標行、E7/E8は注記データ行を持つ"""
        for t in b"678":
            with self.subTest(t=t):
                self.assertTrue(_has_following_lines(t))


class TestClassify(unittest.TestCase):
    def test_too_few_records_raises_value_error(self):
        """3行未満のレコードでValueErrorが発生する"""
        with self.assertRaises(ValueError):
            classify(iter([b"line1", b"line2"]))

    def test_index_records_count(self):
        """インデックスレコードが3つ返される"""
        records = [b"idx1", b"idx2", b"idx3"]
        result = classify(iter(records))
        self.assertEqual(len(result.index_records), 3)

    def test_map_sheet_collected_until_header(self):
        """H行が来るまでを図郭レコードとして収集する"""
        records = [
            b"M index_a",
            b"  index_b",
            b"  index_c",
            b"sheet_line_1",
            b"sheet_line_2",
            b"H 2100 header",
            b"E22101 element",
        ]
        result = classify(iter(records))
        self.assertEqual(len(result.map_sheet_records), 2)
        self.assertEqual(result.map_sheet_records[0], b"sheet_line_1")

    def test_element_group_structure(self):
        """H + E の構造が ElementGroup として返される"""
        records = [
            b"idx_a",
            b"idx_b",
            b"idx_c",
            b"H 2100 header1",
            b"E52101 point_element",
            b"E52102 point_element2",
            b"H 3000 header2",
            b"E73001 annotation",
        ]
        result = classify(iter(records))
        self.assertEqual(len(result.element_groups), 2)
        self.assertEqual(len(result.element_groups[0].elements), 2)
        self.assertEqual(len(result.element_groups[1].elements), 1)

    def test_e2_has_coordinate_lines(self):
        """E2要素の後続行が座標行として収集される"""
        records = [
            b"idx_a",
            b"idx_b",
            b"idx_c",
            b"H 2100 header",
            b"E22101 line_element",
            b"1106380 6343101106470 6324501106590 6297801105640 625000",
            b"1098860 6134201097140 6079701096700 6026601096980 600070",
        ]
        result = classify(iter(records))
        elem = result.element_groups[0].elements[0]
        self.assertEqual(len(elem.coordinate_lines), 2)

    def test_e5_has_no_coordinate_lines(self):
        """E5要素は座標行を持たない"""
        records = [
            b"idx_a",
            b"idx_b",
            b"idx_c",
            b"H 2100 header",
            b"E52101 point_element",
        ]
        result = classify(iter(records))
        elem = result.element_groups[0].elements[0]
        self.assertEqual(elem.coordinate_lines, ())

    def test_modification_history_skipped(self):
        """修正履歴レコードが出力に含まれない"""
        # 位置79に"1"を持つレコード
        history = b" " * 79 + b"1"
        records = [
            b"idx_a",
            b"idx_b",
            b"idx_c",
            history,  # 図郭フェーズでスキップされるべき
            b"H 2100 header",
            b"E52101 point_element",
        ]
        result = classify(iter(records))
        self.assertEqual(len(result.map_sheet_records), 0)

    def test_g_and_t_records_skipped(self):
        """G/Tレコードがスキップされる"""
        records = [
            b"idx_a",
            b"idx_b",
            b"idx_c",
            b"H 2100 header",
            b"G grid_record",
            b"T tin_record",
            b"E52101 point_element",
        ]
        result = classify(iter(records))
        self.assertEqual(len(result.element_groups[0].elements), 1)


class TestClassifyWithSampleData(unittest.TestCase):
    def test_returns_classified_records(self):
        """サンプルDMファイルからClassifiedRecordsが返される"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                result = classify(read_records(dm_path))
                self.assertIsInstance(result, ClassifiedRecords)

    def test_index_records_first_starts_with_m(self):
        """インデックスレコードの先頭が"M "で始まる"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                result = classify(read_records(dm_path))
                self.assertTrue(result.index_records[0].startswith(b"M "))

    def test_map_sheet_records_not_empty(self):
        """図郭レコードが空でない"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                result = classify(read_records(dm_path))
                self.assertGreater(len(result.map_sheet_records), 0)

    def test_element_groups_not_empty(self):
        """要素グループが空でない"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                result = classify(read_records(dm_path))
                self.assertGreater(len(result.element_groups), 0)

    def test_all_headers_start_with_h(self):
        """全グループのヘッダーが"H "で始まる"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                result = classify(read_records(dm_path))
                for group in result.element_groups:
                    self.assertTrue(
                        group.header.startswith(b"H "),
                        f"ヘッダーが'H 'で始まらない: {group.header[:20]}",
                    )

    def test_no_modification_history_in_output(self):
        """図郭・H行・E行に修正履歴レコードが含まれない"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                result = classify(read_records(dm_path))
                for rec in result.map_sheet_records:
                    self.assertFalse(
                        _is_modification_history(rec),
                        f"修正履歴が図郭に含まれている: {rec[:20]}",
                    )
                for group in result.element_groups:
                    self.assertFalse(_is_modification_history(group.header))
                    for elem in group.elements:
                        self.assertFalse(_is_modification_history(elem.record))


if __name__ == "__main__":
    unittest.main()
