"""DmToGeoPackageAlgorithm のパラメータ定義のユニットテスト"""

import unittest

from core.dmconverter.algorithm_geopackage_converter import DmToGeoPackageAlgorithm
from core.dmconverter.writer.writer import (
    DEFAULT_LAYER_GRANULARITY,
    LAYER_GRANULARITY_OPTIONS,
)
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
