import os
import unittest

from core.dmconverter.parser.classifier import classify
from core.dmconverter.parser.models import (
    Coordinate,
    ParsedDM,
)
from core.dmconverter.parser.parser import (
    _decode_old_jis_text,
    _extract_common_fields,
    _format_date,
    _parse_annotation_element,
    _parse_coordinate_line_2d,
    _parse_coordinate_line_3d,
    _parse_map_sheet,
    _parse_mesh_info,
    _parse_point_element,
    _safe_int,
    parse,
)
from core.dmconverter.parser.reader import detect_encoding, read_records

# テスト用DMファイル（tests/scripts/generate_test_data.py が生成する合成データ）
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SAMPLE_DM_FILES = [
    os.path.join(DATA_DIR, "synthetic_cs06_1000_cp932.dm"),
    os.path.join(DATA_DIR, "synthetic_cs09_1000_utf8_bom.dm"),
    os.path.join(DATA_DIR, "synthetic_cs12_2500_cp932_rev3.dm"),
    os.path.join(DATA_DIR, "synthetic_cs08_2500_oldjis.dm"),
    os.path.join(DATA_DIR, "synthetic_cs01_500_utf8_lf.dm"),
]
CP932_DM_FILE = SAMPLE_DM_FILES[0]
CIRCLE_DM_FILE = SAMPLE_DM_FILES[2]
OLD_JIS_DM_FILE = SAMPLE_DM_FILES[3]

# synthetic_cs06_1000_cp932.dm に含まれるレコード（84バイト、デコード済み文字列）
E2_RECORD = "E22101 0   0   1 2 02350 00   8   2      0      0      0 0       200300000000       "
E5_RECORD = "E57311 0   0  13 2 02350 00   0   0 250000 500000  12345 1       200300000000       "
E7_RECORD = "E78121 0   0  16 2 02351 00   4   1  56000 300000      0 0       200300000000       "
E7_ANNOTATION_LINE = "1    -45   30   10 4合成通り"
# 座標行: 6組ちょうど / 2組 + 余白(0, 0)
FULL_COORD_LINE = "  90000  40000  90000 140000  90000 240000  90000 340000  90000 440000  90000 540000"
PADDED_COORD_LINE = "  63000 520000  63000 600000      0      0      0      0      0      0      0      0"


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
    def test_full_line(self):
        """座標行（6組ちょうど）を正しく解析する"""
        coords = _parse_coordinate_line_2d(FULL_COORD_LINE, 6)
        self.assertEqual(len(coords), 6)
        self.assertEqual(coords[0], Coordinate(x=90000, y=40000))
        self.assertEqual(coords[1], Coordinate(x=90000, y=140000))
        self.assertEqual(coords[5], Coordinate(x=90000, y=540000))

    def test_line_with_padding(self):
        """パディング（0, 0）ペアを含む行"""
        coords = _parse_coordinate_line_2d(PADDED_COORD_LINE, 6)
        self.assertEqual(len(coords), 2)
        self.assertEqual(coords[0], Coordinate(x=63000, y=520000))
        self.assertEqual(coords[1], Coordinate(x=63000, y=600000))

    def test_remaining_limits_output(self):
        """remainingで座標数を制限できる"""
        coords = _parse_coordinate_line_2d(FULL_COORD_LINE, 2)
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
        fields = _extract_common_fields(E2_RECORD)
        self.assertEqual(fields["element_type"], "E2")
        self.assertEqual(fields["dm_code"], "2101")
        self.assertEqual(fields["chiiki_bunrui"], 0)
        self.assertEqual(fields["jouhou_bunrui"], 0)
        self.assertEqual(fields["element_id"], 1)
        self.assertEqual(fields["hierarchy"], 2)
        self.assertEqual(fields["data_kubun"], 2)
        self.assertEqual(fields["seido_kubun"], 35)
        self.assertEqual(fields["coord_count"], 8)
        self.assertEqual(fields["record_count"], 2)
        self.assertEqual(fields["acquired_date"], "2020/03")
        self.assertIsNone(fields["updated_date"])
        self.assertIsNone(fields["deleted_date"])

    def test_e5_record(self):
        """E5レコードから共通フィールドを抽出する"""
        fields = _extract_common_fields(E5_RECORD)
        self.assertEqual(fields["element_type"], "E5")
        self.assertEqual(fields["dm_code"], "7311")
        self.assertEqual(fields["chiiki_bunrui"], 0)
        self.assertEqual(fields["jouhou_bunrui"], 0)
        self.assertEqual(fields["element_id"], 13)
        self.assertEqual(fields["coord_count"], 0)

    def test_chiiki_and_jouhou_bunrui_field_widths(self):
        """chiiki_bunrui(I2) と jouhou_bunrui(I4) のオフセット・桁数を検証する"""
        record = "E22101 21234   0 1212 00 00  80  14      0      0      0 0       170300000000      1"
        fields = _extract_common_fields(record)
        self.assertEqual(fields["chiiki_bunrui"], 2)  # record[6:8]  = " 2"
        self.assertEqual(fields["jouhou_bunrui"], 1234)  # record[8:12] = "1234"


class TestParsePointElement(unittest.TestCase):
    def test_e5_embedded_coordinates(self):
        """E5要素の埋め込み座標と属性数値・属性区分を正しく解析する"""
        elem = _parse_point_element(E5_RECORD, [])
        self.assertEqual(elem.element_type, "E5")
        self.assertEqual(elem.dm_code, "7311")
        self.assertEqual(len(elem.coordinates), 1)
        self.assertEqual(elem.coordinates[0].x, 250000)
        self.assertEqual(elem.coordinates[0].y, 500000)
        self.assertEqual(elem.attribute_value, 12345)
        self.assertEqual(elem.zokusei_kubun, 1)

    def test_e5_short_record_returns_empty_coordinates(self):
        """E5レコードが58bytes未満の場合、座標なしで返しwarningを追加する"""
        short_record = E5_RECORD[:35]
        warnings: list[str] = []
        elem = _parse_point_element(short_record, warnings)
        self.assertEqual(elem.coordinates, ())
        self.assertEqual(len(warnings), 1)
        self.assertIn("不正なレコード長", warnings[0])


class TestParseMeshInfo(unittest.TestCase):
    def _make_mesh_rows(self, sheet_id: bytes) -> tuple:
        rec_type = b"M "  # 2 bytes
        map_name = "合成原".encode("shift_jis").ljust(20)  # 20 bytes
        level = b" 1000"  # 5 bytes
        line_a = (rec_type + sheet_id + map_name + level).ljust(84)
        # (b): 左下(12000, 8000) 右上(12600, 8800)、座標単位 1(mm) は バイト44-46
        line_b = b"  12000   8000  12600   8800" + b" " * 16 + b"  1" + b" " * 37
        return (line_a, line_b, b" " * 84)

    def test_coordinate_system(self):
        """図郭識別番号の先頭2文字から座標系番号を抽出する"""
        mesh_rows = self._make_mesh_rows(b"02SYN013")
        info = _parse_mesh_info(mesh_rows, "shift_jis")
        self.assertEqual(info.coordinate_system, 2)
        self.assertEqual(info.map_name, "合成原")
        self.assertEqual(info.scale, 1000)

    def test_coordinate_system_from_index_record(self):
        """Iレコードがある場合、図郭識別番号より優先して座標系番号を取得する"""
        # 図郭識別番号は02系だがIレコードで6系を指定
        mesh_rows = self._make_mesh_rows(b"02SYN013")
        index_row = b"I  6" + b" " * 80  # 座標系6
        info = _parse_mesh_info(mesh_rows, "shift_jis", index_row=index_row)
        self.assertEqual(info.coordinate_system, 6)

    def test_coordinate_system_none_when_invalid_sheet_id(self):
        """仕様外の図郭識別番号（先頭2文字が1-19範囲外）はNoneを返す"""
        mesh_rows = self._make_mesh_rows(b"2914    ")
        info = _parse_mesh_info(mesh_rows, "shift_jis")
        self.assertIsNone(info.coordinate_system)

    def test_coordinate_system_none_when_index_record_invalid(self):
        """Iレコードの座標系が範囲外の場合、図郭識別番号にフォールバックする"""
        mesh_rows = self._make_mesh_rows(b"02SYN013")
        index_row = b"I 99" + b" " * 80  # 座標系99（無効）
        info = _parse_mesh_info(mesh_rows, "shift_jis", index_row=index_row)
        # Iレコードが無効なので図郭識別番号の02系を使う
        self.assertEqual(info.coordinate_system, 2)


class TestParseAnnotationElement(unittest.TestCase):
    def test_e7_coordinates(self):
        """E7要素の代表点座標を正しく解析する"""
        record = E7_RECORD
        annotation_line = E7_ANNOTATION_LINE
        elem = _parse_annotation_element(record, (annotation_line,), [])
        self.assertEqual(elem.element_type, "E7")
        self.assertEqual(elem.dm_code, "8121")
        self.assertEqual(len(elem.coordinates), 1)
        self.assertEqual(elem.coordinates[0].x, 56000)
        self.assertEqual(elem.coordinates[0].y, 300000)

    def test_e7_annotation_info(self):
        """E7要素の注記情報を正しく解析する"""
        record = E7_RECORD
        annotation_line = E7_ANNOTATION_LINE
        elem = _parse_annotation_element(record, (annotation_line,), [])
        assert elem.annotation is not None
        self.assertEqual(elem.annotation.orientation, 1)
        self.assertEqual(elem.annotation.angle, -45)
        self.assertEqual(elem.annotation.size, 30)
        self.assertEqual(elem.annotation.spacing, 10)
        self.assertEqual(elem.annotation.line_weight, 4)
        self.assertEqual(elem.annotation.text, "合成通り")

    def test_e7_no_annotation_lines(self):
        """後続行がない場合、annotationはNone"""
        record = E7_RECORD
        elem = _parse_annotation_element(record, (), [])
        self.assertIsNone(elem.annotation)
        self.assertEqual(len(elem.coordinates), 1)

    def test_e7_short_record_returns_empty_coordinates(self):
        """E7レコードが56bytes未満の場合、座標なしで返しwarningを追加する"""
        short_record = E7_RECORD[:35]
        warnings: list[str] = []
        elem = _parse_annotation_element(short_record, (), warnings)
        self.assertEqual(elem.coordinates, ())
        self.assertEqual(len(warnings), 1)
        self.assertIn("不正なレコード長", warnings[0])

    def test_e7_short_annotation_line_returns_no_annotation(self):
        """後続行が20bytes未満の場合、座標はあるがannotationなしでwarningを追加する"""
        record = E7_RECORD
        short_annotation = "0    -28   15"  # 13bytes
        warnings: list[str] = []
        elem = _parse_annotation_element(record, (short_annotation,), warnings)
        self.assertEqual(len(elem.coordinates), 1)
        self.assertIsNone(elem.annotation)
        self.assertEqual(len(warnings), 1)
        self.assertIn("不正な注記後続レコード長", warnings[0])


class TestParseE7WithSampleData(unittest.TestCase):
    def test_e7_elements_have_coordinates_and_annotation(self):
        """サンプルデータのE7要素が座標と注記情報を持つ"""
        dm_path = CP932_DM_FILE
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

    def test_parse_warnings_empty_for_valid_data(self):
        """正常なDMファイルではparse_warningsが空タプルであること"""
        for dm_path in SAMPLE_DM_FILES:
            with self.subTest(dm_path=dm_path):
                result = parse(
                    classify(read_records(dm_path), detect_encoding(dm_path))
                )
                self.assertEqual(result.parse_warnings, ())

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
        dm_path = CP932_DM_FILE
        classified = classify(read_records(dm_path), detect_encoding(dm_path))
        info = _parse_map_sheet(classified.mesh_rows)
        self.assertLess(info.origin_x, info.upper_x)
        self.assertLess(info.origin_y, info.upper_y)
        self.assertIn(info.coord_unit, (1, 10, 999))


class TestDecodeOldJisText(unittest.TestCase):
    def test_full_width_digits(self):
        """#X パターンが全角数字にデコードされること"""
        # #0#1#2 → ０１２（EUC-JP A3B0 A3B1 A3B2 の各バイト - 0x80）
        result = _decode_old_jis_text("#0#1#2")
        self.assertEqual(result, "０１２")

    def test_katakana(self):
        """%X パターンが全角カタカナにデコードされること"""
        # %F%9%H → テスト（EUC-JP A5C6 A5B9 A5C8 の各バイト - 0x80）
        result = _decode_old_jis_text("%F%9%H")
        self.assertEqual(result, "テスト")

    def test_fullwidth_space_padding(self):
        """!! が全角スペースにデコードされること"""
        result = _decode_old_jis_text("!!")
        self.assertEqual(result, "\u3000")  # 全角スペース

    def test_mixed_digits_and_padding(self):
        """図郭名フィールド相当（数字+全角スペースパディング）のデコード"""
        # "#0#1#2!!!!!!!!!!!!!!" (3文字+7スペース=20バイト) → デコード後 strip で全角スペース除去
        result = _decode_old_jis_text("#0#1#2!!!!!!!!!!!!!!")
        self.assertEqual(result.strip(), "０１２")

    def test_numeric_text_returns_str(self):
        """数値のみのテキストは文字列として返ること（EUC-JPとして変換される場合がある）"""
        result = _decode_old_jis_text("12345678")
        # 数値の場合は EUC-JP として有効な場合もあるため、例外が出ないことを確認
        self.assertIsInstance(result, str)

    def test_odd_length_passthrough(self):
        """奇数長の文字列はそのまま返ること"""
        result = _decode_old_jis_text("abc")
        self.assertEqual(result, "abc")

    def test_empty_string(self):
        """空文字列は空文字列を返すこと"""
        result = _decode_old_jis_text("")
        self.assertEqual(result, "")


class TestParseMeshInfoOldJis(unittest.TestCase):
    # 旧型式（7bit JIS）合成データの M レコード(a)行（84バイト、全バイト ASCII）
    _MESH_ROW = next(iter(read_records(OLD_JIS_DM_FILE)))

    def test_map_name_decoded(self):
        """old_jis エンコーディングで図郭名が正しくデコードされること"""
        info = _parse_mesh_info((TestParseMeshInfoOldJis._MESH_ROW,), "old_jis")
        self.assertEqual(info.map_name, "合成図郭Ｄ")

    def test_map_name_no_trailing_fullwidth_space(self):
        """デコード後の図郭名に末尾の全角スペースが含まれないこと"""
        info = _parse_mesh_info((TestParseMeshInfoOldJis._MESH_ROW,), "old_jis")
        self.assertFalse(info.map_name.endswith("\u3000"))

    def test_scale_parsed(self):
        """縮尺が正しく取得されること"""
        info = _parse_mesh_info((TestParseMeshInfoOldJis._MESH_ROW,), "old_jis")
        self.assertEqual(info.scale, 2500)


if __name__ == "__main__":
    unittest.main()
