"""ジオメトリ変換関数のユニットテスト

QgsCircle等のQGISクラスを使用するため、QGIS環境の初期化が必要。
"""

import os
import unittest

from tests.utilities import get_qgis_app

get_qgis_app()  # QgsCircle等を使用するためにQGISを初期化

from core.dmconverter.parser.classifier import classify
from core.dmconverter.parser.parser import parse
from core.dmconverter.parser.reader import detect_encoding, read_records
from core.dmconverter.writer.geometry import to_circle_geometry
from qgis.core import QgsWkbTypes

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CIRCLE_DM_FILE = os.path.join(
    DATA_DIR, "円10件(円弧4件)_08DF013_新潟市中央区拡張2500.dm"
)


class TestToCircleGeometry(unittest.TestCase):
    """to_circle_geometry 関数のユニットテスト"""

    @classmethod
    def setUpClass(cls):
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


if __name__ == "__main__":
    unittest.main()
