"""スタイル適用（writer/style.py）のユニットテスト

QGISのレイヤ・レンダラーを扱うため、QGIS環境の初期化が必要。
フィクスチャ tests/fixtures/point_form_test.qml は
HCODE2（ValueMap）・分類コード（TextEdit, 編集不可, 更新時デフォルト式）・
字の大きさ（Range, 制約式）の3フィールド分のフォーム設定を持つ点用QML。
"""

import os
import unittest

from qgis.core import (
    QgsNullSymbolRenderer,
    QgsRenderContext,
    QgsVectorLayer,
    QgsWkbTypes,
)

from core.dmconverter.writer.style import (
    QmlStyle,
    _parse_qml_document,
    apply_layer_style,
    apply_qml_by_geom_type,
    apply_qml_form,
    build_qml_map,
    build_style_cache,
)
from tests.utilities import get_qgis_app

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")

# フィクスチャQMLが設定を持つ3フィールド + QMLに存在しない1フィールド（独自列）
POINT_LAYER_URI = (
    "Point?crs=EPSG:6677"
    "&field=HCODE2:string"
    "&field=分類コード:string"
    "&field=字の大きさ:integer"
    "&field=独自列:string"
)
# フィクスチャには線用QMLがないため、キャッシュに存在しないジオメトリタイプとして使う
LINE_LAYER_URI = "LineString?crs=EPSG:6677&field=HCODE2:string"


def _make_layer(uri: str, name: str = "test") -> QgsVectorLayer:
    layer = QgsVectorLayer(uri, name, "memory")
    assert layer.isValid(), f"メモリレイヤの作成に失敗: {uri}"
    return layer


class TestBuildStyleCache(unittest.TestCase):
    """build_style_cache: QMLをジオメトリタイプ別にレンダラー+DOMでキャッシュする"""

    @classmethod
    def setUpClass(cls):
        get_qgis_app()
        cls.cache = build_style_cache(build_qml_map(FIXTURE_DIR))

    def test_point_entry_is_qml_style(self):
        """点用QMLが点ジオメトリのキーで QmlStyle として登録される"""
        self.assertIn(QgsWkbTypes.PointGeometry, self.cache)
        self.assertIsInstance(self.cache[QgsWkbTypes.PointGeometry], QmlStyle)

    def test_renderer_is_categorized(self):
        """レンダラーはQMLどおりカテゴリ分け"""
        renderer = self.cache[QgsWkbTypes.PointGeometry].renderer
        self.assertEqual(renderer.type(), "categorizedSymbol")
        self.assertEqual(len(renderer.categories()), 2)

    def test_document_root_is_qgis(self):
        """DOMのルート要素は <qgis>"""
        document = self.cache[QgsWkbTypes.PointGeometry].document
        self.assertEqual(document.documentElement().tagName(), "qgis")

    def test_parse_failure_returns_none(self):
        """壊れたXMLは _parse_qml_document が None を返す"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            broken = os.path.join(tmpdir, "broken.qml")
            with open(broken, "w", encoding="utf-8") as f:
                f.write("<qgis><renderer-v2>")
            self.assertIsNone(_parse_qml_document(broken))


class TestApplyQmlForm(unittest.TestCase):
    """apply_qml_form: Fields/Forms だけをレイヤに適用する"""

    @classmethod
    def setUpClass(cls):
        get_qgis_app()
        cls.cache = build_style_cache(build_qml_map(FIXTURE_DIR))

    def test_applies_widgets_and_field_settings(self):
        """ウィジェット・別名・labelOnTop・編集可否・デフォルト式・制約式が反映される"""
        layer = _make_layer(POINT_LAYER_URI)
        self.assertTrue(apply_qml_form(layer, self.cache))
        fields = layer.fields()
        form = layer.editFormConfig()

        i_hcode = fields.lookupField("HCODE2")
        self.assertEqual(layer.editorWidgetSetup(i_hcode).type(), "ValueMap")
        self.assertEqual(layer.attributeAlias(i_hcode), "地物コード（HCODE2）")
        self.assertTrue(form.labelOnTop(i_hcode))

        i_code = fields.lookupField("分類コード")
        self.assertTrue(form.readOnly(i_code))
        default = layer.defaultValueDefinition(i_code)
        self.assertEqual(default.expression(), 'left("HCODE2", 4)')
        self.assertTrue(default.applyOnUpdate())

        i_size = fields.lookupField("字の大きさ")
        self.assertEqual(layer.editorWidgetSetup(i_size).type(), "Range")
        self.assertEqual(layer.editorWidgetSetup(i_size).config()["Max"], 99999)
        self.assertIn('"字の大きさ" IS NULL', layer.constraintExpression(i_size))

    def test_field_missing_in_qml_is_untouched(self):
        """QMLに設定がないフィールドはデフォルト（ウィジェット未指定・別名なし）のまま"""
        layer = _make_layer(POINT_LAYER_URI)
        apply_qml_form(layer, self.cache)
        i = layer.fields().lookupField("独自列")
        self.assertEqual(layer.editorWidgetSetup(i).type(), "")
        self.assertEqual(layer.attributeAlias(i), "")

    def test_keeps_renderer(self):
        """フォーム適用はレンダラーを変更しない（注記レイヤのNullSymbolが残る）"""
        layer = _make_layer(POINT_LAYER_URI)
        layer.setRenderer(QgsNullSymbolRenderer())
        apply_qml_form(layer, self.cache)
        self.assertEqual(layer.renderer().type(), "nullSymbol")

    def test_unknown_geometry_returns_false(self):
        """キャッシュにないジオメトリタイプは False を返し、何も変えない"""
        layer = _make_layer(LINE_LAYER_URI)
        self.assertFalse(apply_qml_form(layer, self.cache))
        i = layer.fields().lookupField("HCODE2")
        self.assertEqual(layer.editorWidgetSetup(i).type(), "")

    def test_empty_cache_returns_false(self):
        """空キャッシュでは False"""
        layer = _make_layer(POINT_LAYER_URI)
        self.assertFalse(apply_qml_form(layer, {}))


class TestApplyQmlByGeomType(unittest.TestCase):
    """apply_qml_by_geom_type: QmlStyle キャッシュからレンダラーだけを適用する"""

    @classmethod
    def setUpClass(cls):
        get_qgis_app()
        cls.cache = build_style_cache(build_qml_map(FIXTURE_DIR))

    def test_applies_categorized_renderer(self):
        """点レイヤにカテゴリ分けレンダラー（シンボル2件）が複製される"""
        layer = _make_layer(POINT_LAYER_URI)
        self.assertTrue(apply_qml_by_geom_type(layer, self.cache))
        self.assertEqual(layer.renderer().type(), "categorizedSymbol")
        self.assertEqual(len(layer.renderer().symbols(QgsRenderContext())), 2)

    def test_does_not_touch_form(self):
        """レンダラー適用だけではフォーム設定は変わらない"""
        layer = _make_layer(POINT_LAYER_URI)
        apply_qml_by_geom_type(layer, self.cache)
        i = layer.fields().lookupField("HCODE2")
        self.assertEqual(layer.editorWidgetSetup(i).type(), "")

    def test_unknown_geometry_returns_false(self):
        """キャッシュにないジオメトリタイプは False でレンダラー未変更"""
        layer = _make_layer(LINE_LAYER_URI)
        self.assertFalse(apply_qml_by_geom_type(layer, self.cache))
        self.assertEqual(layer.renderer().type(), "singleSymbol")


class TestApplyLayerStyle(unittest.TestCase):
    """apply_layer_style: レイヤ1件分の処理列（ラベル/レンダラー/フォーム/回転/間断）"""

    @classmethod
    def setUpClass(cls):
        get_qgis_app()
        cls.cache = build_style_cache(build_qml_map(FIXTURE_DIR))

    def test_annotation_layer(self):
        """注記: ラベル有効・NullSymbol・フォーム適用の3点が揃う"""
        layer = _make_layer(POINT_LAYER_URI)
        apply_layer_style(layer, self.cache, is_annotation=True, is_direction=False)
        self.assertTrue(layer.labelsEnabled())
        self.assertEqual(layer.renderer().type(), "nullSymbol")
        i = layer.fields().lookupField("HCODE2")
        self.assertEqual(layer.editorWidgetSetup(i).type(), "ValueMap")

    def test_regular_layer(self):
        """非注記: QMLレンダラー + フォーム。ラベルは無効のまま"""
        layer = _make_layer(POINT_LAYER_URI)
        apply_layer_style(layer, self.cache, is_annotation=False, is_direction=False)
        self.assertEqual(layer.renderer().type(), "categorizedSymbol")
        self.assertFalse(layer.labelsEnabled())
        i = layer.fields().lookupField("HCODE2")
        self.assertEqual(layer.editorWidgetSetup(i).type(), "ValueMap")
        self.assertTrue(
            layer.editFormConfig().readOnly(layer.fields().lookupField("分類コード"))
        )

    def test_kandan_filter_runs_last_and_keeps_form(self):
        """間断区分フィールドがあればルールベースに変換され、フォーム設定は残る"""
        layer = _make_layer(POINT_LAYER_URI + "&field=間断区分:integer")
        apply_layer_style(layer, self.cache, is_annotation=False, is_direction=False)
        self.assertEqual(layer.renderer().type(), "RuleRenderer")
        i = layer.fields().lookupField("HCODE2")
        self.assertEqual(layer.editorWidgetSetup(i).type(), "ValueMap")

    def test_empty_cache_is_safe(self):
        """空キャッシュ（スタイルフォルダ未指定）でも例外なく動き、レンダラーは既定のまま"""
        layer = _make_layer(POINT_LAYER_URI)
        apply_layer_style(layer, {}, is_annotation=False, is_direction=False)
        self.assertEqual(layer.renderer().type(), "singleSymbol")
        i = layer.fields().lookupField("HCODE2")
        self.assertEqual(layer.editorWidgetSetup(i).type(), "")
