"""DmToGeoPackageAlgorithm のパラメータ定義・レイヤツリー配置のユニットテスト"""

import os
import tempfile
import unittest

from qgis.core import (
    QgsLayerTreeGroup,
    QgsLayerTreeLayer,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProject,
)

from core.dmconverter.algorithm_geopackage_converter import DmToGeoPackageAlgorithm
from core.dmconverter.writer.writer import (
    DEFAULT_LAYER_GRANULARITY,
    LAYER_GRANULARITY_OPTIONS,
    create_merged_layers,
    save_to_geopackage,
)
from tests.unit.test_writer import _lines_and_polygons
from tests.utilities import get_qgis_app


class TestLayerGranularityParameter(unittest.TestCase):
    """「レイヤ分割：分類コードの粒度」Enum パラメータ"""

    @classmethod
    def setUpClass(cls):
        get_qgis_app()

    def _parameter(self):
        # algorithm をローカル変数のままにすると関数を抜けた時点でGCされ、
        # 返り値の parameterDefinition が指す C++ 側オブジェクトも
        # 一緒に破棄されてしまう（"wrapped C/C++ object ... has been
        # deleted"）。self に保持して algorithm の生存期間をテストメソッド
        # 実行中まで延ばす。
        self._algorithm = DmToGeoPackageAlgorithm()
        self._algorithm.initAlgorithm()
        return self._algorithm.parameterDefinition(
            DmToGeoPackageAlgorithm.LAYER_GRANULARITY
        )

    def test_parameter_exists(self):
        self.assertIsNotNone(self._parameter())

    def test_options_follow_writer_definition(self):
        self.assertEqual(
            self._parameter().options(),
            [label for _, label in LAYER_GRANULARITY_OPTIONS],
        )

    def test_default_index_maps_to_default_granularity(self):
        index = self._parameter().defaultValue()
        self.assertEqual(LAYER_GRANULARITY_OPTIONS[index][0], DEFAULT_LAYER_GRANULARITY)

    def test_description(self):
        self.assertEqual(
            self._parameter().description(), "レイヤ分割：分類コードの粒度"
        )


class TestPostProcessLayerTree(unittest.TestCase):
    """postProcessAlgorithm が作るレイヤツリー配置（サブグループ / DM直下）"""

    @classmethod
    def setUpClass(cls):
        get_qgis_app()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _run(self, granularity: str, group_name: str) -> tuple[list[str], list[str]]:
        result = create_merged_layers([_lines_and_polygons()], granularity)
        gpkg = os.path.join(self._tmp.name, f"{granularity}.gpkg")
        self.assertEqual(save_to_geopackage(result.layers, gpkg), [])

        # algorithm を self に保持し、テストメソッド実行中の生存期間を延ばす
        # （_parameter() と同様、SIP ラップされたオブジェクトの早期解放を防ぐ）
        self._alg = DmToGeoPackageAlgorithm()
        self._alg.initAlgorithm()
        self._alg._output_path = gpkg
        self._alg._layer_names = [layer.name() for layer in result.layers]
        self._alg._layer_parent_codes = result.layer_parent_codes
        self._alg._style_folder = ""
        self._alg._group_name = group_name

        context = QgsProcessingContext()
        context.setProject(QgsProject.instance())
        self._alg.postProcessAlgorithm(context, QgsProcessingFeedback())

        group = QgsProject.instance().layerTreeRoot().findGroup(group_name)
        self.assertIsNotNone(group)

        def _cleanup():
            QgsProject.instance().removeMapLayers(
                [node.layerId() for node in group.findLayers()]
            )
            QgsProject.instance().layerTreeRoot().removeChildNode(group)

        self.addCleanup(_cleanup)

        sub_group_names = sorted(
            child.name()
            for child in group.children()
            if isinstance(child, QgsLayerTreeGroup)
        )
        direct_layer_names = sorted(
            child.layer().name()
            for child in group.children()
            if isinstance(child, QgsLayerTreeLayer)
        )
        return sub_group_names, direct_layer_names

    def test_code4_layers_go_into_subgroups(self):
        sub_groups, direct_layers = self._run("code4", "DM_code4")
        self.assertEqual(sub_groups, ["建物", "諸地・場地", "道路", "道路施設"])
        self.assertEqual(direct_layers, [])

    def test_code2_layers_go_into_subgroups(self):
        sub_groups, direct_layers = self._run("code2", "DM_code2")
        self.assertEqual(sub_groups, ["建物", "諸地・場地", "道路", "道路施設"])
        self.assertEqual(direct_layers, [])

    def test_none_layers_go_directly_under_group(self):
        sub_groups, direct_layers = self._run("none", "DM_none")
        self.assertEqual(sub_groups, [])
        self.assertEqual(direct_layers, ["線", "面"])

    def test_none_creates_no_empty_named_group(self):
        self._run("none", "DM_none2")
        group = QgsProject.instance().layerTreeRoot().findGroup("DM_none2")
        self.assertIsNone(group.findGroup(""))
