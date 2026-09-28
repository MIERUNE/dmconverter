"""ジオメトリ変換関数のユニットテスト

QgsCircle等のQGISクラスを使用するため、QGIS環境の初期化が必要。
"""

import os
import unittest

from core.dmconverter.parser.classifier import classify
from core.dmconverter.parser.parser import parse
from core.dmconverter.parser.reader import detect_encoding, read_records
from core.dmconverter.parser.models import Coordinate, MapSheetInfo, ParsedElement
from core.dmconverter.writer.geometry import (
    group_ring_polygons,
    to_arc_geometry,
    to_circle_geometry,
    to_ring_polygon_geometry,
)
from qgis.core import QgsWkbTypes
from tests.utilities import get_qgis_app

# テスト用DMファイル（tests/scripts/generate_test_data.py が生成する合成データ）
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CIRCLE_DM_FILE = os.path.join(DATA_DIR, "synthetic_cs12_2500_cp932_rev3.dm")


class TestToCircleGeometry(unittest.TestCase):
    """to_circle_geometry 関数のユニットテスト"""

    @classmethod
    def setUpClass(cls):
        get_qgis_app()
        classified = classify(
            read_records(CIRCLE_DM_FILE), detect_encoding(CIRCLE_DM_FILE)
        )
        parsed = parse(classified)
        cls.map_sheet = parsed.map_sheet
        cls.e3_elements = [
            elem
            for group in parsed.groups
            for elem in group.elements
            if elem.element_type == "E3"
        ]

    def test_e3_elements_exist(self):
        """円データファイルにE3要素が含まれる（前提確認）"""
        self.assertGreater(len(self.e3_elements), 0, "E3要素が見つからない")

    def test_returns_polygon_geometry(self):
        """to_circle_geometry がPolygonジオメトリを返す"""
        for elem in self.e3_elements:
            with self.subTest(element_id=elem.element_id):
                geom = to_circle_geometry(elem, self.map_sheet)
                self.assertFalse(geom.isEmpty(), "生成されたジオメトリが空")
                self.assertEqual(
                    geom.type(),
                    QgsWkbTypes.PolygonGeometry,
                    "ジオメトリタイプがPolygonでない",
                )

    def test_polygon_ring_is_closed(self):
        """生成された円ポリゴンの外周リングが閉じている（始点==終点）"""
        for elem in self.e3_elements:
            with self.subTest(element_id=elem.element_id):
                geom = to_circle_geometry(elem, self.map_sheet)
                ring = geom.asPolygon()[0]
                self.assertEqual(
                    (ring[0].x(), ring[0].y()),
                    (ring[-1].x(), ring[-1].y()),
                    "リングが閉じていない",
                )


class TestToArcGeometry(unittest.TestCase):
    """to_arc_geometry 関数のユニットテスト"""

    @classmethod
    def setUpClass(cls):
        get_qgis_app()
        classified = classify(
            read_records(CIRCLE_DM_FILE), detect_encoding(CIRCLE_DM_FILE)
        )
        parsed = parse(classified)
        cls.map_sheet = parsed.map_sheet
        cls.e4_elements = [
            elem
            for group in parsed.groups
            for elem in group.elements
            if elem.element_type == "E4"
        ]

    def test_e4_elements_exist(self):
        """円弧データファイルにE4要素が含まれる（前提確認）"""
        self.assertGreater(len(self.e4_elements), 0, "E4要素が見つからない")

    def test_returns_line_geometry(self):
        """to_arc_geometry がLineStringジオメトリを返す"""
        for elem in self.e4_elements:
            with self.subTest(element_id=elem.element_id):
                geom = to_arc_geometry(elem, self.map_sheet)
                self.assertFalse(geom.isEmpty(), "生成されたジオメトリが空")
                self.assertEqual(
                    geom.type(),
                    QgsWkbTypes.LineGeometry,
                    "ジオメトリタイプがLineStringでない",
                )


def _make_element(zukei_kubun: int, coords: list[tuple[int, int]]) -> ParsedElement:
    """テスト用の ParsedElement を生成するヘルパー。"""
    return ParsedElement(
        element_type="E1",
        dm_code="3001",
        chiiki_bunrui=0,
        jouhou_bunrui=0,
        element_id=1,
        hierarchy=2,
        zukei_kubun=zukei_kubun,
        data_kubun=2,
        seido_kubun=36,
        chuki_kubun=0,
        teni=0,
        kandan=0,
        coordinates=tuple(Coordinate(x=x, y=y) for x, y in coords),
    )


# 座標単位 999=m: origin_x/y=0 で _to_abs_point(x,y) → QgsPointXY(y, x)
_MS = MapSheetInfo(origin_x=0, origin_y=0, upper_x=1000, upper_y=1000, coord_unit=999)

# 外周: 原点中心 100×100 の正方形（閉じていない座標列でも fromPolygonXY が閉じる）
_OUTER_COORDS = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
# 内輪（中庭）: 外周の内部にある 10×10 の正方形
_INNER_COORDS = [(10, 10), (20, 10), (20, 20), (10, 20), (10, 10)]
# 外周の外にある内輪
_OUTSIDE_COORDS = [(200, 200), (300, 200), (300, 300), (200, 300), (200, 200)]


class TestToRingPolygonGeometry(unittest.TestCase):
    """to_ring_polygon_geometry 関数のユニットテスト"""

    @classmethod
    def setUpClass(cls):
        get_qgis_app()

    def test_returns_polygon_with_two_rings(self):
        """外輪 + 内輪1つでリングが2つのポリゴンが生成される"""
        outer = _make_element(0, _OUTER_COORDS)
        inner = _make_element(31, _INNER_COORDS)
        geom = to_ring_polygon_geometry(outer, _MS, [(inner, _MS)])
        self.assertFalse(geom.isEmpty())
        self.assertEqual(geom.type(), QgsWkbTypes.PolygonGeometry)
        self.assertEqual(len(geom.asPolygon()), 2, "リング数が2でない（外輪+内輪）")

    def test_inner_uses_its_own_map_sheet(self):
        """内輪が異なる MapSheetInfo を持つ場合でも正しく座標変換される"""
        inner_ms = MapSheetInfo(
            origin_x=0, origin_y=100, upper_x=200, upper_y=200, coord_unit=999
        )
        outer = _make_element(0, _OUTER_COORDS)
        inner = _make_element(
            31, [(10, -90), (20, -90), (20, -80), (10, -80), (10, -90)]
        )
        geom = to_ring_polygon_geometry(outer, _MS, [(inner, inner_ms)])
        self.assertFalse(geom.isEmpty())
        rings = geom.asPolygon()
        self.assertEqual(len(rings), 2)
        # 内輪の Y座標: origin_y=100 + (-90)/1 = 10 → 外輪内部に収まっている
        inner_ring = rings[1]
        for pt in inner_ring:
            self.assertGreater(pt.x(), 0)
            self.assertLess(pt.x(), 100)


class TestGroupRingPolygons(unittest.TestCase):
    """group_ring_polygons 関数のユニットテスト"""

    @classmethod
    def setUpClass(cls):
        get_qgis_app()

    def test_no_inner_returns_empty(self):
        """内輪なしのとき空リストを返す"""
        outer = _make_element(0, _OUTER_COORDS)
        result = group_ring_polygons([(outer, _MS)])
        self.assertEqual(result, [])

    def test_inner_matched_to_outer(self):
        """内輪が外輪に内包される場合、ペアとして返す"""
        outer = _make_element(0, _OUTER_COORDS)
        inner = _make_element(31, _INNER_COORDS)
        result = group_ring_polygons([(outer, _MS), (inner, _MS)])
        self.assertEqual(len(result), 1)
        out_elem, out_ms, inners = result[0]
        self.assertEqual(out_elem.zukei_kubun, 0)
        self.assertEqual(len(inners), 1)
        self.assertEqual(inners[0][0].zukei_kubun, 31)

    def test_inner_not_contained_is_standalone(self):
        """外輪に内包されない内輪は単独（inners=[]）として返す"""
        outer = _make_element(0, _OUTER_COORDS)
        outside_inner = _make_element(31, _OUTSIDE_COORDS)
        result = group_ring_polygons([(outer, _MS), (outside_inner, _MS)])
        # 外輪1つ（内輪なし） + 外れ内輪1つ（単独）= 計2エントリ
        self.assertEqual(len(result), 2)
        standalone = next(r for r in result if r[0].zukei_kubun == 31)
        self.assertEqual(standalone[2], [], "外れ内輪のinnersが空でない")

    def test_multiple_inners(self):
        """複数の内輪が同一外輪にまとめられる"""
        outer = _make_element(0, _OUTER_COORDS)
        inner1 = _make_element(31, _INNER_COORDS)
        inner2 = _make_element(31, [(30, 30), (40, 30), (40, 40), (30, 40), (30, 30)])
        result = group_ring_polygons([(outer, _MS), (inner1, _MS), (inner2, _MS)])
        self.assertEqual(len(result), 1)
        _, _, inners = result[0]
        self.assertEqual(len(inners), 2)


if __name__ == "__main__":
    unittest.main()
