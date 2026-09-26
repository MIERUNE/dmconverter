"""writer.create_merged_layers のレイヤ分割粒度のユニットテスト

tests/data/ は gitignore で空のため、ParsedDM をメモリ上で組み立てる。
座標単位は 999（m）で、原点 (0, 0) の図郭に小さな整数座標を置く。
"""

import unittest

from core.dmconverter.parser.models import (
    Coordinate,
    MapSheetInfo,
    MeshInfo,
    ParsedDM,
    ParsedElement,
    ParsedGroup,
)
from core.dmconverter.writer.writer import (
    DEFAULT_LAYER_GRANULARITY,
    LAYER_GRANULARITY_OPTIONS,
    _layer_code,
)
from tests.utilities import get_qgis_app

MAP_SHEET = MapSheetInfo(
    origin_x=0, origin_y=0, upper_x=1000, upper_y=1000, coord_unit=999
)
MESH_INFO = MeshInfo(coordinate_system=9, map_name="test", scale=2500)


def _element(
    element_type: str,
    dm_code: str,
    element_id: int,
    coords: list[tuple[int, int]],
    zukei_kubun: int = 0,
) -> ParsedElement:
    return ParsedElement(
        element_type=element_type,
        dm_code=dm_code,
        chiiki_bunrui=0,
        jouhou_bunrui=0,
        element_id=element_id,
        hierarchy=0,
        zukei_kubun=zukei_kubun,
        data_kubun=2,
        seido_kubun=0,
        chuki_kubun=0,
        teni=0,
        kandan=0,
        coordinates=tuple(Coordinate(x, y) for x, y in coords),
    )


def _square(x0: int, y0: int, size: int) -> list[tuple[int, int]]:
    """左下 (x0, y0) の閉じた正方形の座標列"""
    return [
        (x0, y0),
        (x0 + size, y0),
        (x0 + size, y0 + size),
        (x0, y0 + size),
        (x0, y0),
    ]


def _dm(*elements: ParsedElement) -> ParsedDM:
    return ParsedDM(
        mesh_info=MESH_INFO,
        map_sheet=MAP_SHEET,
        groups=(ParsedGroup(dm_code=elements[0].dm_code, elements=tuple(elements)),),
    )


class TestLayerGranularityDefinitions(unittest.TestCase):
    """粒度定義と _layer_code"""

    @classmethod
    def setUpClass(cls):
        get_qgis_app()

    def test_default_is_an_option(self):
        keys = [key for key, _ in LAYER_GRANULARITY_OPTIONS]
        self.assertIn(DEFAULT_LAYER_GRANULARITY, keys)

    def test_option_keys_are_unique(self):
        keys = [key for key, _ in LAYER_GRANULARITY_OPTIONS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_option_labels(self):
        labels = [label for _, label in LAYER_GRANULARITY_OPTIONS]
        self.assertEqual(
            labels, ["分類コード4桁", "分類コード2桁", "分類コードで分けない"]
        )

    def test_layer_code_code4(self):
        self.assertEqual(_layer_code("2101", "code4"), "2101")

    def test_layer_code_code2(self):
        self.assertEqual(_layer_code("2101", "code2"), "21")

    def test_layer_code_none(self):
        self.assertEqual(_layer_code("2101", "none"), "")

    def test_layer_code_unknown_raises(self):
        with self.assertRaises(ValueError):
            _layer_code("2101", "xxx")
