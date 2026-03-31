import os
import unittest

from core.dmconverter.classifier import classify
from core.dmconverter.parser.models import (
    Coordinate,
    ParsedDM,
)
from core.dmconverter.parser.parser import (
    _extract_common_fields,
    _parse_coordinate_line_2d,
    _parse_coordinate_line_3d,
    _parse_mesh_info,
    _parse_point_element,
    _safe_int,
    parse,
)
from core.dmconverter.reader import detect_encoding, read_records

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SAMPLE_DM_FILES = [
    os.path.join(DATA_DIR, "02JF613.dm"),
    os.path.join(DATA_DIR, "02JF711.dm"),
]


class TestSafeInt(unittest.TestCase):
    def test_normal_integer(self):
        self.assertEqual(_safe_int("42"), 42)

    def test_padded_with_spaces(self):
        self.assertEqual(_safe_int("  80"), 80)

    def test_empty_string(self):
        self.assertEqual(_safe_int(""), 0)

    def test_spaces_only(self):
        self.assertEqual(_safe_int("   "), 0)

    def test_negative(self):
        self.assertEqual(_safe_int("-5"), -5)

    def test_non_numeric(self):
        self.assertEqual(_safe_int("abc"), 0)

    def test_custom_default(self):
        self.assertEqual(_safe_int("", default=-1), -1)


class TestParseCoordinateLine2d(unittest.TestCase):
    def test_full_line_from_sample(self):
        """サンプルデータの実座標行（6組）を正しく解析する"""
        # 02JF613.dm 12行目のデータ
        line = "1106380 6343101106470 6324501106590 6297801105640 6250001103280 6213101099910 616240"
        coords = _parse_coordinate_line_2d(line, 6)
        self.assertEqual(len(coords), 6)
        self.assertEqual(coords[0], Coordinate(x=1106380, y=634310))
        self.assertEqual(coords[1], Coordinate(x=1106470, y=632450))
        self.assertEqual(coords[5], Coordinate(x=1099910, y=616240))

    def test_line_with_padding(self):
        """パディング（0, 0）ペアを含む行"""
        line = " 4533511745422 4567361736530      0      0      0      0      0      0      0      0"
        coords = _parse_coordinate_line_2d(line, 6)
        self.assertEqual(len(coords), 2)
        self.assertEqual(coords[0], Coordinate(x=453351, y=1745422))
        self.assertEqual(coords[1], Coordinate(x=456736, y=1736530))

    def test_remaining_limits_output(self):
        """remainingで座標数を制限できる"""
        line = "1106380 6343101106470 6324501106590 6297801105640 6250001103280 6213101099910 616240"
        coords = _parse_coordinate_line_2d(line, 2)
        self.assertEqual(len(coords), 2)


class TestParseCoordinateLine3d(unittest.TestCase):
    def test_basic_3d_line(self):
        """3D座標行を正しく解析する"""
        # 7文字×3=21文字×4組=84文字
        line = " 100000 200000 000050 300000 400000 000100      0      0      0      0      0      0"
        coords = _parse_coordinate_line_3d(line, 4)
        self.assertEqual(len(coords), 2)
        self.assertEqual(coords[0], Coordinate(x=100000, y=200000, z=50))
        self.assertEqual(coords[1], Coordinate(x=300000, y=400000, z=100))


class TestExtractCommonFields(unittest.TestCase):
    def test_e2_record(self):
        """E2レコードから共通フィールドを抽出する"""
        record = "E22101 0   0   1 2152350 00  80  14      0      0      0 0       170300000000      1"
        fields = _extract_common_fields(record)
        self.assertEqual(fields["element_type"], "E2")
        self.assertEqual(fields["dm_code"], "2101")
        self.assertEqual(fields["hierarchy"], 1)
        self.assertEqual(fields["data_kubun"], 2)
        self.assertEqual(fields["coord_count"], 80)
        self.assertEqual(fields["record_count"], 14)

    def test_e5_record(self):
        """E5レコードから共通フィールドを抽出する"""
        record = "E52253 0   0   1 2 00350 00   0   0 7530601721853      0 0       170300000000      1"
        fields = _extract_common_fields(record)
        self.assertEqual(fields["element_type"], "E5")
        self.assertEqual(fields["dm_code"], "2253")
        self.assertEqual(fields["coord_count"], 0)


class TestParsePointElement(unittest.TestCase):
    def test_e5_embedded_coordinates(self):
        """E5要素の埋め込み座標を正しく解析する"""
        record = "E52253 0   0   1 2 00350 00   0   0 7530601721853      0 0       170300000000      1"
        elem = _parse_point_element(record)
        self.assertEqual(elem.element_type, "E5")
        self.assertEqual(elem.dm_code, "2253")
        self.assertEqual(len(elem.coordinates), 1)
        self.assertEqual(elem.coordinates[0].x, 753060)
        self.assertEqual(elem.coordinates[0].y, 1721853)


class TestParseMeshInfo(unittest.TestCase):
    def test_coordinate_system(self):
        """図郭レコードから座標系番号を抽出する"""
        mesh_rows = (
            "M 02JF613 地形測量               1000啪市立用パデータ           111               ".encode(
                "utf-8"
            ),
            "   9000  44000  10500  46000    26332  80920  1  10500  44000   9000  46000         ".encode(
                "utf-8"
            ),
            "02JF602 02JF611                         02JF711 02JF702 02JF604                     ".encode(
                "utf-8"
            ),
        )
        info = _parse_mesh_info(mesh_rows, "utf-8")
        self.assertEqual(info.coordinate_system, 2)
        self.assertEqual(info.scale, 1000)


class TestParseWithSampleData(unittest.TestCase):
    def test_returns_parsed_dm(self):
        """サンプルDMファイルからParsedDMが返される"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                result = parse(
                    classify(read_records(dm_path), detect_encoding(dm_path))
                )
                self.assertIsInstance(result, ParsedDM)

    def test_index_has_valid_coordinate_system(self):
        """座標系番号が1-19の範囲内"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                result = parse(
                    classify(read_records(dm_path), detect_encoding(dm_path))
                )
                self.assertGreaterEqual(result.mesh_info.coordinate_system, 1)
                self.assertLessEqual(result.mesh_info.coordinate_system, 19)

    def test_groups_not_empty(self):
        """グループが空でない"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                result = parse(
                    classify(read_records(dm_path), detect_encoding(dm_path))
                )
                self.assertGreater(len(result.groups), 0)

    def test_all_dm_codes_are_4_digits(self):
        """全dm_codeが4桁文字列"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                result = parse(
                    classify(read_records(dm_path), detect_encoding(dm_path))
                )
                for group in result.groups:
                    self.assertEqual(
                        len(group.dm_code),
                        4,
                        f"グループdm_codeが4桁でない: '{group.dm_code}'",
                    )
                    for elem in group.elements:
                        self.assertEqual(
                            len(elem.dm_code),
                            4,
                            f"要素dm_codeが4桁でない: '{elem.dm_code}'",
                        )

    def test_e2_elements_have_coordinates(self):
        """E2要素が座標を持つ"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                result = parse(
                    classify(read_records(dm_path), detect_encoding(dm_path))
                )
                e2_found = False
                for group in result.groups:
                    for elem in group.elements:
                        if elem.element_type == "E2":
                            e2_found = True
                            self.assertGreater(
                                len(elem.coordinates),
                                0,
                                "E2要素の座標が空",
                            )
                self.assertTrue(e2_found, "E2要素が見つからない")

    def test_e5_elements_have_one_coordinate(self):
        """E5要素が1つの座標を持つ"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                result = parse(
                    classify(read_records(dm_path), detect_encoding(dm_path))
                )
                for group in result.groups:
                    for elem in group.elements:
                        if elem.element_type == "E5":
                            self.assertEqual(
                                len(elem.coordinates),
                                1,
                                "E5要素の座標が1つでない",
                            )

    def test_e6_elements_have_coordinates(self):
        """E6要素が座標を持つ"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                result = parse(
                    classify(read_records(dm_path), detect_encoding(dm_path))
                )
                for group in result.groups:
                    for elem in group.elements:
                        if elem.element_type == "E6":
                            self.assertGreater(
                                len(elem.coordinates),
                                0,
                                "E6要素の座標が空",
                            )


if __name__ == "__main__":
    unittest.main()
