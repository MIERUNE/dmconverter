"""ApplyStyleAlgorithm のサブグループ判定（_resolve_parent_code）・
postProcessAlgorithm のレイヤツリー配置のユニットテスト
"""

from __future__ import annotations

import os
import tempfile
import unittest

from qgis.core import (
    NULL,
    QgsFeature,
    QgsLayerTreeGroup,
    QgsLayerTreeLayer,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProject,
    QgsVectorLayer,
)

from core.dmconverter.algorithm_apply_style import (
    ApplyStyleAlgorithm,
    _resolve_parent_code,
)
from core.dmconverter.writer.writer import create_merged_layers, save_to_geopackage
from tests.unit.test_writer import _lines_and_polygons
from tests.utilities import get_qgis_app

HCODE2_LAYER_URI = "Point?crs=EPSG:6677&field=HCODE2:string"


def _layer_with_hcode2(values: list[str | None]) -> QgsVectorLayer:
    """HCODE2 に values を持つメモリレイヤ。None は NULL として登録する"""
    layer = QgsVectorLayer(HCODE2_LAYER_URI, "test", "memory")
    features = []
    for value in values:
        feat = QgsFeature(layer.fields())
        feat.setAttribute("HCODE2", NULL if value is None else value)
        features.append(feat)
    layer.dataProvider().addFeatures(features)
    return layer


class TestResolveParentCode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        get_qgis_app()

    def test_single_prefix(self):
        layer = _layer_with_hcode2(["210101", "210201"])
        self.assertEqual(_resolve_parent_code(layer), "21")

    def test_mixed_prefixes_returns_none(self):
        layer = _layer_with_hcode2(["210101", "300101"])
        self.assertIsNone(_resolve_parent_code(layer))

    def test_missing_field_returns_empty(self):
        layer = QgsVectorLayer("Point?crs=EPSG:6677&field=name:string", "t", "memory")
        self.assertEqual(_resolve_parent_code(layer), "")

    def test_no_features_returns_empty(self):
        self.assertEqual(_resolve_parent_code(_layer_with_hcode2([])), "")

    def test_null_values_are_ignored(self):
        layer = _layer_with_hcode2([None, "210101"])
        self.assertEqual(_resolve_parent_code(layer), "21")

    def test_only_null_returns_empty(self):
        self.assertEqual(_resolve_parent_code(_layer_with_hcode2([None])), "")


class TestPostProcessLayerTree(unittest.TestCase):
    """postProcessAlgorithm が作るレイヤツリー配置（サブグループ / DM直下）"""

    @classmethod
    def setUpClass(cls):
        get_qgis_app()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._styles_dir = os.path.join(self._tmp.name, "styles")
        os.makedirs(self._styles_dir)

    def _run(self, granularity: str) -> tuple[list[str], list[str]]:
        result = create_merged_layers([_lines_and_polygons()], granularity)
        gpkg = os.path.join(self._tmp.name, f"{granularity}.gpkg")
        self.assertEqual(save_to_geopackage(result.layers, gpkg), [])

        # algorithm を self に保持し、テストメソッド実行中の生存期間を延ばす
        self._alg = ApplyStyleAlgorithm()
        self._alg.initAlgorithm()
        self._alg._gpkg_files = [gpkg]
        self._alg._style_folder = self._styles_dir

        context = QgsProcessingContext()
        context.setProject(QgsProject.instance())
        self._alg.postProcessAlgorithm(context, QgsProcessingFeedback())

        group = QgsProject.instance().layerTreeRoot().findGroup("DM")
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

    def test_mixed_layers_go_directly_under_dm(self):
        """HCODE2 の上位2桁が混在するレイヤ（分けない）はDM直下"""
        sub_groups, direct_layers = self._run("none")
        self.assertEqual(sub_groups, [])
        self.assertEqual(direct_layers, ["線", "面"])

    def test_single_prefix_layers_go_into_subgroups(self):
        sub_groups, direct_layers = self._run("code2")
        self.assertEqual(sub_groups, ["建物", "諸地・場地", "道路", "道路施設"])
        self.assertEqual(direct_layers, [])
