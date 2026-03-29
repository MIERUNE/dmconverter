import os
import unittest

from core.dmconverter.classifier import classify
from core.dmconverter.parser.models import (
    AnnotationInfo,
    AttributeInfo,
    Coordinate,
    ParsedDM,
)
from core.dmconverter.parser.parser import (
    _extract_common_fields,
    _parse_annotation_element,
    _parse_attribute_element,
    _parse_coordinate_line_2d,
    _parse_coordinate_line_3d,
    _parse_index,
    _parse_map_sheet,
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
        self.assertEqual(_safe_int(b"42"), 42)

    def test_padded_with_spaces(self):
        self.assertEqual(_safe_int(b"  80"), 80)

    def test_empty_bytes(self):
        self.assertEqual(_safe_int(b""), 0)

    def test_spaces_only(self):
        self.assertEqual(_safe_int(b"   "), 0)

    def test_negative(self):
        self.assertEqual(_safe_int(b"-5"), -5)

    def test_non_numeric(self):
        self.assertEqual(_safe_int(b"abc"), 0)

    def test_custom_default(self):
        self.assertEqual(_safe_int(b"", default=-1), -1)


class TestParseCoordinateLine2d(unittest.TestCase):
    def test_full_line_from_sample(self):
        """サンプルデータの実座標行（6組）を正しく解析する"""
        # 02JF613.dm 12行目のデータ
        line = b"1106380 6343101106470 6324501106590 6297801105640 6250001103280 6213101099910 616240"
        coords = _parse_coordinate_line_2d(line, 6)
        self.assertEqual(len(coords), 6)
        self.assertEqual(coords[0], Coordinate(x=1106380, y=634310))
        self.assertEqual(coords[1], Coordinate(x=1106470, y=632450))
        self.assertEqual(coords[5], Coordinate(x=1099910, y=616240))

    def test_line_with_padding(self):
        """パディング（0, 0）ペアを含む行"""
        line = b" 4533511745422 4567361736530      0      0      0      0      0      0      0      0"
        coords = _parse_coordinate_line_2d(line, 6)
        self.assertEqual(len(coords), 2)
        self.assertEqual(coords[0], Coordinate(x=453351, y=1745422))
        self.assertEqual(coords[1], Coordinate(x=456736, y=1736530))

    def test_remaining_limits_output(self):
        """remainingで座標数を制限できる"""
        line = b"1106380 6343101106470 6324501106590 6297801105640 6250001103280 6213101099910 616240"
        coords = _parse_coordinate_line_2d(line, 2)
        self.assertEqual(len(coords), 2)


class TestParseCoordinateLine3d(unittest.TestCase):
    def test_basic_3d_line(self):
        """3D座標行を正しく解析する"""
        # 7文字×3=21文字×4組=84文字
        line = b" 100000 200000 000050 300000 400000 000100      0      0      0      0      0      0"
        coords = _parse_coordinate_line_3d(line, 4)
        self.assertEqual(len(coords), 2)
        self.assertEqual(coords[0], Coordinate(x=100000, y=200000, z=50))
        self.assertEqual(coords[1], Coordinate(x=300000, y=400000, z=100))


class TestExtractCommonFields(unittest.TestCase):
    def test_e2_record(self):
        """E2レコードから共通フィールドを抽出する"""
        record = b"E22101 0   0   1 2152350 00  80  14      0      0      0 0       170300000000      1"
        fields = _extract_common_fields(record)
        self.assertEqual(fields["element_type"], "E2")
        self.assertEqual(fields["dm_code"], "2101")
        self.assertEqual(fields["hierarchy"], 1)
        self.assertEqual(fields["data_kubun"], 2)
        self.assertEqual(fields["coord_count"], 80)
        self.assertEqual(fields["record_count"], 14)

    def test_e5_record(self):
        """E5レコードから共通フィールドを抽出する"""
        record = b"E52253 0   0   1 2 00350 00   0   0 7530601721853      0 0       170300000000      1"
        fields = _extract_common_fields(record)
        self.assertEqual(fields["element_type"], "E5")
        self.assertEqual(fields["dm_code"], "2253")
        self.assertEqual(fields["coord_count"], 0)


class TestParsePointElement(unittest.TestCase):
    def test_e5_embedded_coordinates(self):
        """E5要素の埋め込み座標を正しく解析する"""
        record = b"E52253 0   0   1 2 00350 00   0   0 7530601721853      0 0       170300000000      1"
        elem = _parse_point_element(record)
        self.assertEqual(elem.element_type, "E5")
        self.assertEqual(elem.dm_code, "2253")
        self.assertEqual(len(elem.coordinates), 1)
        self.assertEqual(elem.coordinates[0].x, 753060)
        self.assertEqual(elem.coordinates[0].y, 1721853)


class TestParseIndex(unittest.TestCase):
    def test_coordinate_system(self):
        """インデックスレコードから座標系番号を抽出する"""
        dm_path = SAMPLE_DM_FILES[0]  # 02JF613.dm
        encoding = detect_encoding(dm_path)
        records = list(read_records(dm_path))
        index_records = (records[0], records[1], records[2])
        info = _parse_index(index_records, encoding)
        self.assertEqual(info.coordinate_system, 2)
        self.assertEqual(info.scale, 1000)


class TestParseWithSampleData(unittest.TestCase):
    def test_returns_parsed_dm(self):
        """サンプルDMファイルからParsedDMが返される"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                encoding = detect_encoding(dm_path)
                result = parse(classify(read_records(dm_path)), encoding)
                self.assertIsInstance(result, ParsedDM)

    def test_index_has_valid_coordinate_system(self):
        """座標系番号が1-19の範囲内"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                encoding = detect_encoding(dm_path)
                result = parse(classify(read_records(dm_path)), encoding)
                self.assertGreaterEqual(result.index.coordinate_system, 1)
                self.assertLessEqual(result.index.coordinate_system, 19)

    def test_groups_not_empty(self):
        """グループが空でない"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                encoding = detect_encoding(dm_path)
                result = parse(classify(read_records(dm_path)), encoding)
                self.assertGreater(len(result.groups), 0)

    def test_all_dm_codes_are_4_digits(self):
        """全dm_codeが4桁文字列"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                encoding = detect_encoding(dm_path)
                result = parse(classify(read_records(dm_path)), encoding)
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
                encoding = detect_encoding(dm_path)
                result = parse(classify(read_records(dm_path)), encoding)
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
                encoding = detect_encoding(dm_path)
                result = parse(classify(read_records(dm_path)), encoding)
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
                encoding = detect_encoding(dm_path)
                result = parse(classify(read_records(dm_path)), encoding)
                for group in result.groups:
                    for elem in group.elements:
                        if elem.element_type == "E6":
                            self.assertGreater(
                                len(elem.coordinates),
                                0,
                                "E6要素の座標が空",
                            )


class TestParseAnnotationElement(unittest.TestCase):
    def test_e7_coordinates(self):
        """E7要素の代表点座標を正しく解析する"""
        record = b"E77101 0   0   2 2 04352 00   3   11079383 996705        0       170300000000      1"
        annotation_line = b"0    -28   15    0 4410                                                             "
        elem = _parse_annotation_element(record, (annotation_line,), "ascii")
        self.assertEqual(elem.element_type, "E7")
        self.assertEqual(elem.dm_code, "7101")
        self.assertEqual(len(elem.coordinates), 1)
        self.assertEqual(elem.coordinates[0].x, 1079383)
        self.assertEqual(elem.coordinates[0].y, 996705)

    def test_e7_annotation_info(self):
        """E7要素の注記情報を正しく解析する"""
        record = b"E77101 0   0   2 2 04352 00   3   11079383 996705        0       170300000000      1"
        annotation_line = b"0    -28   15    0 4410                                                             "
        elem = _parse_annotation_element(record, (annotation_line,), "ascii")
        self.assertIsNotNone(elem.annotation)
        self.assertEqual(elem.annotation.orientation, 0)
        self.assertEqual(elem.annotation.angle, -28)
        self.assertEqual(elem.annotation.size, 15)
        self.assertEqual(elem.annotation.spacing, 0)
        self.assertEqual(elem.annotation.line_weight, 4)
        self.assertEqual(elem.annotation.text, "410")

    def test_e7_no_annotation_lines(self):
        """後続行がない場合、annotationはNone"""
        record = b"E77101 0   0   2 2 04352 00   3   11079383 996705        0       170300000000      1"
        elem = _parse_annotation_element(record, (), "ascii")
        self.assertIsNone(elem.annotation)
        self.assertEqual(len(elem.coordinates), 1)


class TestParseAttributeElement(unittest.TestCase):
    def test_e8_coordinates(self):
        """E8要素の代表点座標を正しく解析する"""
        record = b"E87101 0   0   1 2 00350 00   1   1 500000 600000        0       170300000000      1"
        attribute_line = b"12345                                                                               "
        elem = _parse_attribute_element(record, (attribute_line,), "ascii")
        self.assertEqual(elem.element_type, "E8")
        self.assertEqual(len(elem.coordinates), 1)
        self.assertEqual(elem.coordinates[0].x, 500000)
        self.assertEqual(elem.coordinates[0].y, 600000)

    def test_e8_attribute_data(self):
        """E8要素の属性データを正しく解析する"""
        record = b"E87101 0   0   1 2 00350 00   1   1 500000 600000        0       170300000000      1"
        attribute_line = b"12345                                                                               "
        elem = _parse_attribute_element(record, (attribute_line,), "ascii")
        self.assertIsNotNone(elem.attribute)
        self.assertEqual(elem.attribute.data, "12345")

    def test_e8_no_attribute_lines(self):
        """後続行がない場合、attributeはNone"""
        record = b"E87101 0   0   1 2 00350 00   1   1 500000 600000        0       170300000000      1"
        elem = _parse_attribute_element(record, (), "ascii")
        self.assertIsNone(elem.attribute)


class TestParseE7WithSampleData(unittest.TestCase):
    def test_e7_elements_have_coordinates_and_annotation(self):
        """サンプルデータのE7要素が座標と注記情報を持つ"""
        dm_path = SAMPLE_DM_FILES[0]  # 02JF613.dm (437 E7)
        encoding = detect_encoding(dm_path)
        result = parse(classify(read_records(dm_path)), encoding)
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
                    self.assertIsNotNone(
                        elem.annotation,
                        "E7要素のannotationがNone",
                    )
                    self.assertGreater(
                        len(elem.annotation.text),
                        0,
                        "E7要素の注記テキストが空",
                    )
        self.assertGreater(e7_count, 0, "E7要素が見つからない")


class TestParseMapSheet(unittest.TestCase):
    def test_map_sheet_from_sample(self):
        """サンプルデータから図郭情報を正しく抽出する"""
        dm_path = SAMPLE_DM_FILES[0]  # 02JF613.dm
        classified = classify(read_records(dm_path))
        info = _parse_map_sheet(classified.index_records)
        # 左下 < 右上 であること
        self.assertLess(info.origin_x, info.upper_x)
        self.assertLess(info.origin_y, info.upper_y)
        # 座標値の単位が有効な値
        self.assertIn(info.coord_unit, (1, 10, 999))

    def test_parsed_dm_has_map_sheet(self):
        """ParsedDMにmap_sheetが含まれる"""
        dm_path = SAMPLE_DM_FILES[0]
        encoding = detect_encoding(dm_path)
        result = parse(classify(read_records(dm_path)), encoding)
        self.assertIsNotNone(result.map_sheet)
        self.assertGreater(result.map_sheet.origin_x, 0)


if __name__ == "__main__":
    unittest.main()
