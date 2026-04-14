import os
import unittest

from core.dmconverter.parser.classifier import classify
from core.dmconverter.parser.models import (
    Coordinate,
    ParsedDM,
)
from core.dmconverter.parser.parser import (
    _extract_common_fields,
    _format_date,
    _parse_annotation_element,
    _parse_attribute_element,
    _parse_coordinate_line_2d,
    _parse_coordinate_line_3d,
    _parse_map_sheet,
    _parse_mesh_info,
    _parse_point_element,
    _safe_int,
    parse,
)
from core.dmconverter.parser.reader import detect_encoding, read_records

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


class TestFormatDate(unittest.TestCase):
    def test_normal_date(self):
        """正常な4桁日付をYYYY/MM形式に変換する"""
        self.assertEqual(_format_date("1703"), "2017/03")

    def test_20th_century(self):
        """50以上の年は19xx年として扱う"""
        self.assertEqual(_format_date("9901"), "1999/01")

    def test_zero_date(self):
        """0000はNoneを返す"""
        self.assertIsNone(_format_date("0000"))

    def test_empty_string(self):
        """空文字はNoneを返す"""
        self.assertIsNone(_format_date(""))

    def test_invalid_month_13(self):
        """月が13以上はNoneを返す"""
        self.assertIsNone(_format_date("1713"))

    def test_invalid_month_00(self):
        """月が00はNoneを返す"""
        self.assertIsNone(_format_date("1700"))

    def test_short_string(self):
        """3桁以下はNoneを返す"""
        self.assertIsNone(_format_date("123"))

    def test_non_digit(self):
        """数字以外はNoneを返す"""
        self.assertIsNone(_format_date("abcd"))

    def test_spaces(self):
        """空白のみはNoneを返す"""
        self.assertIsNone(_format_date("    "))


class TestParseCoordinateLine2d(unittest.TestCase):
    def test_full_line_from_sample(self):
        """サンプルデータの実座標行（6組）を正しく解析する"""
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
        line = " 100000 200000 000050 300000 400000 000100      0      0      0      0      0      0"
        coords = _parse_coordinate_line_3d(line, 4)
        self.assertEqual(len(coords), 2)
        self.assertEqual(coords[0], Coordinate(x=100000, y=200000, z=50))
        self.assertEqual(coords[1], Coordinate(x=300000, y=400000, z=100))


class TestExtractCommonFields(unittest.TestCase):
    def test_e2_record(self):
        """E2レコードから共通フィールドを抽出する"""
        record = "E22101 0 0 0   0 1212 00 00  80  14      0      0      0 0       170300000000      1"
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
        rec_type = b"M "  # 2 bytes
        sheet_id = b"02JF613 "  # 8 bytes
        map_name = "杵ヶ原".encode("shift_jis").ljust(20)  # 20 bytes
        level = b" 1000"  # 5 bytes
        line_a = rec_type + sheet_id + map_name + level
        line_a = line_a.ljust(84)
        mesh_rows = (
            line_a,
            b"   9000  44000  10500  46000    26332  80920  1  10500  44000   9000  46000         ",
            b"02JF602 02JF611                         02JF711 02JF702 02JF604                     ",
        )
        info = _parse_mesh_info(mesh_rows, "shift_jis")
        self.assertEqual(info.coordinate_system, 2)
        self.assertEqual(info.map_name, "杵ヶ原")
        self.assertEqual(info.scale, 1000)


class TestParseAnnotationElement(unittest.TestCase):
    def test_e7_coordinates(self):
        """E7要素の代表点座標を正しく解析する"""
        record = "E77101 0   0   2 2 04352 00   3   11079383 996705        0       170300000000      1"
        annotation_line = "0    -28   15    0 4410                                                             "
        elem = _parse_annotation_element(record, (annotation_line,))
        self.assertEqual(elem.element_type, "E7")
        self.assertEqual(elem.dm_code, "7101")
        self.assertEqual(len(elem.coordinates), 1)
        self.assertEqual(elem.coordinates[0].x, 1079383)
        self.assertEqual(elem.coordinates[0].y, 996705)

    def test_e7_annotation_info(self):
        """E7要素の注記情報を正しく解析する"""
        record = "E77101 0   0   2 2 04352 00   3   11079383 996705        0       170300000000      1"
        annotation_line = "0    -28   15    0 4410                                                             "
        elem = _parse_annotation_element(record, (annotation_line,))
        assert elem.annotation is not None
        self.assertEqual(elem.annotation.orientation, 0)
        self.assertEqual(elem.annotation.angle, -28)
        self.assertEqual(elem.annotation.size, 15)
        self.assertEqual(elem.annotation.spacing, 0)
        self.assertEqual(elem.annotation.line_weight, 4)
        self.assertEqual(elem.annotation.text, "410")

    def test_e7_no_annotation_lines(self):
        """後続行がない場合、annotationはNone"""
        record = "E77101 0   0   2 2 04352 00   3   11079383 996705        0       170300000000      1"
        elem = _parse_annotation_element(record, ())
        self.assertIsNone(elem.annotation)
        self.assertEqual(len(elem.coordinates), 1)


class TestParseAttributeElement(unittest.TestCase):
    def test_e8_coordinates(self):
        """E8要素の代表点座標を正しく解析する"""
        record = "E87101 0   0   1 2 00350 00   1   1 500000 600000        0       170300000000      1"
        attribute_line = "12345                                                                               "
        elem = _parse_attribute_element(record, (attribute_line,))
        self.assertEqual(elem.element_type, "E8")
        self.assertEqual(len(elem.coordinates), 1)
        self.assertEqual(elem.coordinates[0].x, 500000)
        self.assertEqual(elem.coordinates[0].y, 600000)

    def test_e8_attribute_data(self):
        """E8要素の属性データを正しく解析する"""
        record = "E87101 0   0   1 2 00350 00   1   1 500000 600000        0       170300000000      1"
        attribute_line = "12345                                                                               "
        elem = _parse_attribute_element(record, (attribute_line,))
        assert elem.attribute is not None
        self.assertEqual(elem.attribute.data, "12345")

    def test_e8_no_attribute_lines(self):
        """後続行がない場合、attributeはNone"""
        record = "E87101 0   0   1 2 00350 00   1   1 500000 600000        0       170300000000      1"
        elem = _parse_attribute_element(record, ())
        self.assertIsNone(elem.attribute)


class TestParseE7WithSampleData(unittest.TestCase):
    def test_e7_elements_have_coordinates_and_annotation(self):
        """サンプルデータのE7要素が座標と注記情報を持つ"""
        dm_path = SAMPLE_DM_FILES[0]  # 02JF613.dm (437 E7)
        result = parse(classify(read_records(dm_path), detect_encoding(dm_path)))
        e7_count = 0
        for group in result.groups:
            for elem in group.elements:
                if elem.element_type == "E7":
                    e7_count += 1
                    self.assertEqual(
                        len(elem.coordinates),
                        1,
                        "E7要素の座標が1つでない",
                    )
                    assert elem.annotation is not None, "E7要素のannotationがNone"
                    self.assertGreater(
                        len(elem.annotation.text),
                        0,
                        "E7要素の注記テキストが空",
                    )
        self.assertGreater(e7_count, 0, "E7要素が見つからない")


class TestParseWithSampleData(unittest.TestCase):
    def test_returns_parsed_dm(self):
        """サンプルDMファイルからParsedDMが返される"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                result = parse(
                    classify(read_records(dm_path), detect_encoding(dm_path))
                )
                self.assertIsInstance(result, ParsedDM)

    def test_mesh_info_has_valid_coordinate_system(self):
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

    def test_e1_elements_have_coordinates(self):
        """E1要素が3点以上の座標を持つ"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                result = parse(
                    classify(read_records(dm_path), detect_encoding(dm_path))
                )
                e1_found = False
                for group in result.groups:
                    for elem in group.elements:
                        if elem.element_type == "E1":
                            e1_found = True
                            self.assertGreaterEqual(
                                len(elem.coordinates),
                                3,
                                "E1要素の座標が3点未満",
                            )
                self.assertTrue(e1_found, "E1要素が見つからない")

    def test_e1_elements_form_closed_ring(self):
        """E1要素の座標列が閉じたリングである（先頭点==末尾点）"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                result = parse(
                    classify(read_records(dm_path), detect_encoding(dm_path))
                )
                for group in result.groups:
                    for elem in group.elements:
                        if elem.element_type == "E1":
                            first = elem.coordinates[0]
                            last = elem.coordinates[-1]
                            self.assertEqual(
                                (first.x, first.y),
                                (last.x, last.y),
                                f"E1要素のリングが閉じていない "
                                f"(dm_code={elem.dm_code}, "
                                f"id={elem.element_id})",
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


CIRCLE_DM_FILE = os.path.join(
    DATA_DIR, "円10件(円弧4件)_08DF013_新潟市中央区拡張2500.dm"
)


class TestParseE3WithCircleData(unittest.TestCase):
    """E3（円）要素のパーサーテスト（円データファイルを使用）"""

    @classmethod
    def setUpClass(cls):
        classified = classify(
            read_records(CIRCLE_DM_FILE), detect_encoding(CIRCLE_DM_FILE)
        )
        parsed = parse(classified)
        cls.e3_elements = [
            elem
            for group in parsed.groups
            for elem in group.elements
            if elem.element_type == "E3"
        ]

    def test_e3_elements_exist(self):
        """円データファイルにE3要素が含まれる"""
        self.assertGreater(len(self.e3_elements), 0, "E3要素が見つからない")

    def test_e3_elements_have_three_coordinates(self):
        """E3要素は円周上の3点座標を持つ（公共測量標準図式 第41条）"""
        for elem in self.e3_elements:
            with self.subTest(element_id=elem.element_id):
                self.assertEqual(
                    len(elem.coordinates),
                    3,
                    f"E3要素の座標が3点でない（element_id={elem.element_id}）",
                )

    def test_e3_dm_codes_are_4_digits(self):
        """E3要素のdm_codeが4桁文字列"""
        for elem in self.e3_elements:
            with self.subTest(element_id=elem.element_id):
                self.assertEqual(
                    len(elem.dm_code), 4, f"dm_codeが4桁でない: '{elem.dm_code}'"
                )


class TestParseMapSheet(unittest.TestCase):
    def test_map_sheet_from_sample(self):
        """サンプルデータから図郭情報を正しく抽出する"""
        dm_path = SAMPLE_DM_FILES[0]  # 02JF613.dm
        classified = classify(read_records(dm_path), detect_encoding(dm_path))
        info = _parse_map_sheet(classified.mesh_rows)
        self.assertLess(info.origin_x, info.upper_x)
        self.assertLess(info.origin_y, info.upper_y)
        self.assertIn(info.coord_unit, (1, 10, 999))


if __name__ == "__main__":
    unittest.main()
