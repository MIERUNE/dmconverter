import os
import unittest

from core.dmconverter.parser.classifier import (
    ClassifiedRecords,
    _collect_mesh_rows,
    _get_revision_count,
    _has_following_lines,
    _is_element_prefix,
    _is_header_prefix,
    _is_skip_prefix,
    classify,
)
from core.dmconverter.parser.reader import read_records

# テスト用DMファイル（tests/scripts/generate_test_data.py が生成する合成データ）
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SAMPLE_DM_FILES = [
    os.path.join(DATA_DIR, "synthetic_cs06_1000_cp932.dm"),
    os.path.join(DATA_DIR, "synthetic_cs12_2500_cp932_rev3.dm"),
]

# サンプルDMファイルから実レコードを読み込み、テスト用に各種レコードを取得する
_SAMPLE_RECORDS = list(read_records(SAMPLE_DM_FILES[0]))


def _find_records():
    """サンプルデータから各種レコードのインデックスを取得する"""
    first_h = first_e2 = first_e5 = first_e7 = second_h = None
    e2_coord_indices = []

    for i, r in enumerate(_SAMPLE_RECORDS):
        if first_h is None and _is_header_prefix(r):
            first_h = i
        elif first_h is not None and second_h is None and _is_header_prefix(r):
            second_h = i
        if first_e2 is None and r[0:2] == b"E2":
            first_e2 = i
            j = i + 1
            while j < len(_SAMPLE_RECORDS):
                nr = _SAMPLE_RECORDS[j]
                if _is_header_prefix(nr) or _is_element_prefix(nr):
                    break
                e2_coord_indices.append(j)
                j += 1
        if first_e5 is None and r[0:2] == b"E5":
            first_e5 = i
        if first_e7 is None and r[0:2] == b"E7":
            first_e7 = i

    return {
        "first_h": first_h,
        "second_h": second_h,
        "first_e2": first_e2,
        "e2_coord_indices": e2_coord_indices,
        "first_e5": first_e5,
        "first_e7": first_e7,
    }


_IDX = _find_records()


class TestGetRevisionCount(unittest.TestCase):
    def test_zero_revision(self):
        """修正回数0（新規作成）"""
        record = b"M " + b" " * 63 + b" 0" + b" " * 17
        self.assertEqual(_get_revision_count(record), 0)

    def test_one_revision(self):
        """修正回数1"""
        record = b"M " + b" " * 63 + b" 1" + b" " * 17
        self.assertEqual(_get_revision_count(record), 1)

    def test_sample_data_revision_count(self):
        """サンプルデータから修正回数を取得する"""
        count = _get_revision_count(_SAMPLE_RECORDS[0])
        self.assertGreaterEqual(count, 0)


class TestCollectMeshRows(unittest.TestCase):
    def test_sample_data_mesh_rows(self):
        """サンプルデータのMレコードが正しく収集される"""
        mesh_rows = _collect_mesh_rows(_SAMPLE_RECORDS)
        self.assertTrue(mesh_rows[0].startswith(b"M "))
        self.assertGreaterEqual(len(mesh_rows), 3)  # 最低(a)(b)(c)の3行


class TestIsElementPrefix(unittest.TestCase):
    def test_e1_to_e8(self):
        """E1-E8を正しく判定する（E8は未対応だが認識対象）"""
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

    def test_e6_e7_have_following_lines(self):
        """E6は座標行、E7は注記データ行を持つ"""
        for t in b"67":
            with self.subTest(t=t):
                self.assertTrue(_has_following_lines(t))

    def test_e8_has_no_following_lines(self):
        """E8は未対応のため後続行なし"""
        self.assertFalse(_has_following_lines(ord(b"8")))


class TestClassify(unittest.TestCase):
    """classify() のユニットテスト

    テストデータはサンプルDMファイルから read_records() で読んだ
    84バイト実レコードを使用する。
    """

    def test_too_few_records_raises_value_error(self):
        """3行未満のレコードでValueErrorが発生する"""
        with self.assertRaises(ValueError):
            classify(iter(_SAMPLE_RECORDS[:2]))

    def test_mesh_rows_count(self):
        """Mレコード行数がcourse_countによる可変長として正しく収集される"""
        result = classify(iter(_SAMPLE_RECORDS))
        expected_mesh_rows = _collect_mesh_rows(_SAMPLE_RECORDS)
        self.assertEqual(len(result.mesh_rows), len(expected_mesh_rows))

    def test_mesh_rows_first_starts_with_m(self):
        """Mレコードの先頭が"M "で始まる"""
        result = classify(iter(_SAMPLE_RECORDS))
        self.assertTrue(result.mesh_rows[0].startswith(b"M "))

    def test_element_group_structure(self):
        """H + E の構造が ElementGroup として返される"""
        h1 = _IDX["first_h"]
        h2 = _IDX["second_h"]
        # Mレコード全行 + H1 + 配下要素 + H2 + 配下要素の範囲を切り出す
        mesh_count = len(_collect_mesh_rows(_SAMPLE_RECORDS))
        end = h2 + 2  # H2 + 最低1要素
        records = _SAMPLE_RECORDS[:mesh_count] + _SAMPLE_RECORDS[h1:end]
        result = classify(iter(records))
        self.assertGreaterEqual(len(result.element_groups), 2)
        self.assertGreater(len(result.element_groups[0].elements), 0)

    def test_e2_has_coordinate_lines(self):
        """E2要素の後続行が座標行として収集される"""
        h_idx = _IDX["first_h"]
        e2_idx = _IDX["first_e2"]
        coord_indices = _IDX["e2_coord_indices"]
        last_coord = coord_indices[-1]
        mesh_count = len(_collect_mesh_rows(_SAMPLE_RECORDS))
        records = (
            _SAMPLE_RECORDS[:mesh_count]
            + [_SAMPLE_RECORDS[h_idx]]
            + _SAMPLE_RECORDS[e2_idx : last_coord + 1]
        )
        result = classify(iter(records))
        elem = result.element_groups[0].elements[0]
        self.assertEqual(len(elem.coordinate_lines), len(coord_indices))

    def test_e5_has_no_coordinate_lines(self):
        """E5要素は座標行を持たない"""
        h_idx = _IDX["first_h"]
        e5_idx = _IDX["first_e5"]
        mesh_count = len(_collect_mesh_rows(_SAMPLE_RECORDS))
        records = _SAMPLE_RECORDS[:mesh_count] + [
            _SAMPLE_RECORDS[h_idx],
            _SAMPLE_RECORDS[e5_idx],
        ]
        result = classify(iter(records))
        elem = result.element_groups[0].elements[0]
        self.assertEqual(elem.coordinate_lines, ())

    def test_g_and_t_records_skipped(self):
        """G/Tレコードがスキップされる"""
        h_idx = _IDX["first_h"]
        e5_idx = _IDX["first_e5"]
        g_record = b"G ".ljust(84)
        t_record = b"T ".ljust(84)
        mesh_count = len(_collect_mesh_rows(_SAMPLE_RECORDS))
        records = _SAMPLE_RECORDS[:mesh_count] + [
            _SAMPLE_RECORDS[h_idx],
            g_record,
            t_record,
            _SAMPLE_RECORDS[e5_idx],
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

    def test_mesh_rows_first_starts_with_m(self):
        """Mレコードの先頭が"M "で始まる"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                result = classify(read_records(dm_path))
                self.assertTrue(result.mesh_rows[0].startswith(b"M "))

    def test_mesh_rows_dynamic_count(self):
        """Mレコード行数がcourse_countに基づいて動的に収集される"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                records = list(read_records(dm_path))
                result = classify(iter(records))
                expected_mesh_rows = _collect_mesh_rows(records)
                self.assertEqual(len(result.mesh_rows), len(expected_mesh_rows))

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


if __name__ == "__main__":
    unittest.main()
