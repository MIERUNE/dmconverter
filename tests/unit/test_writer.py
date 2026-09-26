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
    _compose_layer_name,
    _get_layer_name,
    _layer_code,
    create_merged_layers,
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


def _lines_and_polygons() -> ParsedDM:
    """線3件（2101, 2102, 2203）と面2件（6201, 3001）。中庭線なし"""
    return _dm(
        _element("E2", "2101", 1, [(0, 0), (10, 10)]),
        _element("E2", "2102", 2, [(0, 0), (20, 20)]),
        _element("E2", "2203", 3, [(0, 0), (30, 30)]),
        _element("E1", "6201", 10, _square(0, 0, 100)),
        _element("E1", "3001", 11, _square(20, 20, 40)),
    )


def _layer_summary(result) -> dict[str, tuple[int, str]]:
    """{レイヤ名: (フィーチャ数, 親コード)}"""
    return {
        layer.name(): (layer.featureCount(), result.layer_parent_codes[layer.name()])
        for layer in result.layers
    }


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


class TestLayerNameHelpers(unittest.TestCase):
    """_get_layer_name と _compose_layer_name"""

    @classmethod
    def setUpClass(cls):
        get_qgis_app()

    def test_get_layer_name_code4_known(self):
        self.assertEqual(_get_layer_name("2101"), "道路縁(街区線)")

    def test_get_layer_name_code4_zero_zero_uses_group_name(self):
        self.assertEqual(_get_layer_name("2100"), "道路")

    def test_get_layer_name_code4_unknown_data_code(self):
        self.assertEqual(_get_layer_name("2201"), "2201")

    def test_get_layer_name_code4_unknown_parent_code(self):
        self.assertEqual(_get_layer_name("9901"), "9901")

    def test_get_layer_name_code2_known(self):
        self.assertEqual(_get_layer_name("21"), "道路")

    def test_get_layer_name_code2_unknown(self):
        self.assertEqual(_get_layer_name("99"), "99")

    def test_get_layer_name_empty(self):
        self.assertEqual(_get_layer_name(""), "")

    def test_compose_with_data_name(self):
        self.assertEqual(_compose_layer_name("道路", "線"), "道路_線")

    def test_compose_same_as_geom_type(self):
        self.assertEqual(_compose_layer_name("注記", "注記"), "注記")

    def test_compose_empty_data_name(self):
        self.assertEqual(_compose_layer_name("", "面"), "面")


class TestCreateMergedLayersGranularity(unittest.TestCase):
    """粒度ごとのレイヤ名・フィーチャ数・親コード"""

    @classmethod
    def setUpClass(cls):
        get_qgis_app()

    def test_code4_is_default(self):
        default = _layer_summary(create_merged_layers([_lines_and_polygons()]))
        explicit = _layer_summary(
            create_merged_layers([_lines_and_polygons()], "code4")
        )
        self.assertEqual(default, explicit)

    def test_code4_layers(self):
        summary = _layer_summary(create_merged_layers([_lines_and_polygons()], "code4"))
        self.assertEqual(
            summary,
            {
                "道路縁(街区線)_線": (1, "21"),
                "軽車道_線": (1, "21"),
                "道路橋(高架部)_線": (1, "22"),
                "区域界_面": (1, "62"),
                "普通建物_面": (1, "30"),
            },
        )

    def test_code2_layers(self):
        summary = _layer_summary(create_merged_layers([_lines_and_polygons()], "code2"))
        self.assertEqual(
            summary,
            {
                "道路_線": (2, "21"),
                "道路施設_線": (1, "22"),
                "諸地・場地_面": (1, "62"),
                "建物_面": (1, "30"),
            },
        )

    def test_none_layers(self):
        summary = _layer_summary(create_merged_layers([_lines_and_polygons()], "none"))
        self.assertEqual(summary, {"線": (3, ""), "面": (2, "")})

    def test_none_keeps_record_types_separate(self):
        """面(E1)と円(E3)は同じPolygonでも別レイヤのまま"""
        dm = _dm(
            _element("E1", "3001", 1, _square(0, 0, 10)),
            _element("E3", "3001", 2, [(0, 0), (10, 0), (5, 5)]),
        )
        names = sorted(
            layer.name() for layer in create_merged_layers([dm], "none").layers
        )
        self.assertEqual(names, ["円", "面"])

    def test_feature_total_is_same_for_all_granularities(self):
        totals = {
            granularity: sum(
                layer.featureCount()
                for layer in create_merged_layers(
                    [_lines_and_polygons()], granularity
                ).layers
            )
            for granularity, _ in LAYER_GRANULARITY_OPTIONS
        }
        self.assertEqual(totals, {"code4": 5, "code2": 5, "none": 5})

    def test_unknown_parent_code_uses_code_as_name(self):
        dm = _dm(_element("E2", "9901", 1, [(0, 0), (10, 10)]))
        self.assertEqual(
            _layer_summary(create_merged_layers([dm], "code4")), {"9901_線": (1, "99")}
        )
        self.assertEqual(
            _layer_summary(create_merged_layers([dm], "code2")), {"99_線": (1, "99")}
        )

    def test_unknown_granularity_raises(self):
        with self.assertRaises(ValueError):
            create_merged_layers([_lines_and_polygons()], "xxx")

    def test_unknown_granularity_raises_even_without_elements(self):
        empty = ParsedDM(mesh_info=MESH_INFO, map_sheet=MAP_SHEET, groups=())
        with self.assertRaises(ValueError):
            create_merged_layers([empty], "xxx")
