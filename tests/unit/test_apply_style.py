"""ApplyStyleAlgorithm のサブグループ判定（_resolve_parent_code）のユニットテスト"""

import unittest

from qgis.core import NULL, QgsFeature, QgsVectorLayer

from core.dmconverter.algorithm_apply_style import _resolve_parent_code
from tests.utilities import get_qgis_app

HCODE2_LAYER_URI = "Point?crs=EPSG:6677&field=HCODE2:string"


def _layer_with_hcode2(values) -> QgsVectorLayer:
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
