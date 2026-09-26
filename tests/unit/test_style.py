"""スタイル適用（writer/style.py）のユニットテスト

QGISのレイヤ・レンダラーを扱うため、QGIS環境の初期化が必要。
フィクスチャ tests/fixtures/point_form_test.qml は
HCODE2（ValueMap）・分類コード（TextEdit, 編集不可, 更新時デフォルト式）・
字の大きさ（Range, 制約式）の3フィールド分のフォーム設定を持つ点用QML。
"""

import os
import tempfile
import unittest

from qgis.core import (
    QgsLayerDefinition,
    QgsLayerTreeGroup,
    QgsProject,
    QgsRenderContext,
    QgsSymbolLayer,
    QgsVectorLayer,
    QgsWkbTypes,
)

from core.dmconverter.writer.style import (
    QmlStyle,
    StyleCache,
    apply_layer_style,
    build_style_cache,
    export_qlr,
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
# 注記レイヤ・方向レイヤは判定用フィールドの有無で識別される
ANNOTATION_LAYER_URI = POINT_LAYER_URI + "&field=注記内容:string"
DIRECTION_LAYER_URI = POINT_LAYER_URI + "&field=方向角:double"
# キャッシュには点用QMLしかないため、cache-miss のジオメトリタイプとして使う
LINE_LAYER_URI = "LineString?crs=EPSG:6677&field=HCODE2:string"


def _make_layer(uri: str, name: str = "test") -> QgsVectorLayer:
    layer = QgsVectorLayer(uri, name, "memory")
    assert layer.isValid(), f"メモリレイヤの作成に失敗: {uri}"
    return layer


def _point_cache() -> StyleCache:
    """点用エントリだけのキャッシュ（線・面フィクスチャが追加されても cache-miss テストが壊れない）"""
    cache = build_style_cache(FIXTURE_DIR)
    return {QgsWkbTypes.PointGeometry: cache[QgsWkbTypes.PointGeometry]}


def _widget_type(layer: QgsVectorLayer, field_name: str) -> str:
    return layer.editorWidgetSetup(layer.fields().lookupField(field_name)).type()


def _write_qml(folder: str, name: str, content: str) -> None:
    with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
        f.write(content)


class _PointCacheTestCase(unittest.TestCase):
    """点用キャッシュを使うテストの基底クラス。キャッシュはクラスごとに独立に構築する"""

    cache: StyleCache

    @classmethod
    def setUpClass(cls):
        get_qgis_app()
        cls.cache = _point_cache()


class TestBuildStyleCache(unittest.TestCase):
    """build_style_cache: フォルダ内のQMLをジオメトリタイプ別にレンダラー+DOMでキャッシュする"""

    @classmethod
    def setUpClass(cls):
        get_qgis_app()
        cls.cache = build_style_cache(FIXTURE_DIR)

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

    def test_missing_folder_returns_empty(self):
        """存在しないフォルダは空のキャッシュ"""
        self.assertEqual(build_style_cache(os.path.join(FIXTURE_DIR, "nope")), {})

    def test_broken_xml_is_skipped(self):
        """壊れたXMLはスキップされ、キャッシュに入らない"""
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_qml(tmpdir, "broken.qml", "<qgis><renderer-v2>")
            self.assertEqual(build_style_cache(tmpdir), {})

    def test_xml_without_categorized_renderer_is_skipped(self):
        """カテゴリ分類レンダラーを持たないXMLはスキップされる"""
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_qml(tmpdir, "other.qml", "<root><child/></root>")
            _write_qml(
                tmpdir,
                "single.qml",
                '<qgis><renderer-v2 type="singleSymbol"><symbols>'
                '<symbol type="marker" name="0"/></symbols></renderer-v2></qgis>',
            )
            self.assertEqual(build_style_cache(tmpdir), {})


class TestApplyLayerStyle(_PointCacheTestCase):
    """apply_layer_style: レイヤ1件分の処理列（ラベル/レンダラー/フォーム/回転/間断）"""

    def test_regular_layer(self):
        """非注記: QMLのカテゴリ分けレンダラー（シンボル2件）+ フォーム。ラベルは無効のまま"""
        layer = _make_layer(POINT_LAYER_URI)
        apply_layer_style(layer, self.cache)
        self.assertEqual(layer.renderer().type(), "categorizedSymbol")
        self.assertEqual(len(layer.renderer().symbols(QgsRenderContext())), 2)
        self.assertFalse(layer.labelsEnabled())
        self.assertEqual(_widget_type(layer, "HCODE2"), "ValueMap")

    def test_form_settings_are_applied(self):
        """ウィジェット・別名・labelOnTop・編集可否・デフォルト式・制約式が反映される"""
        layer = _make_layer(POINT_LAYER_URI)
        apply_layer_style(layer, self.cache)
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

    def test_annotation_layer(self):
        """注記（注記内容あり）: ラベル有効・NullSymbol・フォーム適用の3点が揃う"""
        layer = _make_layer(ANNOTATION_LAYER_URI)
        apply_layer_style(layer, self.cache)
        self.assertTrue(layer.labelsEnabled())
        self.assertEqual(layer.renderer().type(), "nullSymbol")
        self.assertEqual(_widget_type(layer, "HCODE2"), "ValueMap")

    def test_direction_layer_sets_rotation(self):
        """方向（方向角あり）: QMLレンダラーの各シンボルに回転式が設定され、フォームも適用される"""
        layer = _make_layer(DIRECTION_LAYER_URI)
        apply_layer_style(layer, self.cache)
        self.assertEqual(layer.renderer().type(), "categorizedSymbol")
        symbols = layer.renderer().symbols(QgsRenderContext())
        self.assertEqual(len(symbols), 2)
        for symbol in symbols:
            prop = (
                symbol.symbolLayer(0)
                .dataDefinedProperties()
                .property(QgsSymbolLayer.Property.PropertyAngle)
            )
            self.assertTrue(prop.isActive())
            self.assertEqual(prop.expressionString(), '0 - "方向角"')
        self.assertEqual(_widget_type(layer, "HCODE2"), "ValueMap")

    def test_kandan_filter_runs_last_and_keeps_form(self):
        """間断区分フィールドがあればルールベースに変換され、フォーム設定は残る"""
        layer = _make_layer(POINT_LAYER_URI + "&field=間断区分:integer")
        apply_layer_style(layer, self.cache)
        self.assertEqual(layer.renderer().type(), "RuleRenderer")
        self.assertEqual(_widget_type(layer, "HCODE2"), "ValueMap")

    def test_field_missing_in_qml_is_untouched(self):
        """QMLに設定がないフィールドはデフォルト（ウィジェット未指定・別名なし）のまま"""
        layer = _make_layer(POINT_LAYER_URI)
        apply_layer_style(layer, self.cache)
        i = layer.fields().lookupField("独自列")
        self.assertEqual(layer.editorWidgetSetup(i).type(), "")
        self.assertEqual(layer.attributeAlias(i), "")

    def test_qml_field_absent_from_layer_is_ignored(self):
        """QMLにあってレイヤにないフィールド（分類コード・字の大きさ）は無視され、フィールドも増えない"""
        layer = _make_layer(
            "Point?crs=EPSG:6677&field=HCODE2:string&field=独自列:string"
        )
        apply_layer_style(layer, self.cache)
        self.assertEqual(layer.fields().names(), ["HCODE2", "独自列"])
        self.assertEqual(_widget_type(layer, "HCODE2"), "ValueMap")

    def test_unknown_geometry_is_untouched(self):
        """キャッシュにないジオメトリタイプはレンダラーもフォームも既定のまま"""
        layer = _make_layer(LINE_LAYER_URI)
        apply_layer_style(layer, self.cache)
        self.assertEqual(layer.renderer().type(), "singleSymbol")
        self.assertEqual(_widget_type(layer, "HCODE2"), "")

    def test_empty_cache_is_safe(self):
        """空キャッシュ（スタイルフォルダ未指定）でも例外なく動き、レンダラーは既定のまま"""
        layer = _make_layer(POINT_LAYER_URI)
        apply_layer_style(layer, {})
        self.assertEqual(layer.renderer().type(), "singleSymbol")
        self.assertEqual(_widget_type(layer, "HCODE2"), "")


class TestExportQlrWithForm(_PointCacheTestCase):
    """export_qlr: フォーム設定を適用したレイヤのQLRにフィールド設定が含まれる"""

    def test_qlr_contains_form_settings(self):
        """QLRに fieldConfiguration（ValueMap）・defaults が書き出され、読み戻しても再現される"""
        layer = _make_layer(POINT_LAYER_URI, "qlr_test")
        apply_layer_style(layer, self.cache)
        # QLRエクスポートにはプロジェクト登録が必要
        project = QgsProject.instance()
        project.addMapLayer(layer, False)
        group = QgsLayerTreeGroup()
        group.addLayer(layer)
        loaded_ids: list[str] = []
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                qlr_path = os.path.join(tmpdir, "test.qlr")
                self.assertIsNone(export_qlr(group.children(), qlr_path))
                with open(qlr_path, encoding="utf-8") as f:
                    content = f.read()

                # 読み戻し: QGIS/QField が実際に使う経路でフォーム設定が再現されるか
                loaded_group = QgsLayerTreeGroup()
                ok, err = QgsLayerDefinition.loadLayerDefinition(
                    qlr_path, project, loaded_group
                )
                self.assertTrue(ok, err)
                loaded_layers = [node.layer() for node in loaded_group.findLayers()]
                loaded_ids = [lyr.id() for lyr in loaded_layers]
                self.assertEqual(len(loaded_layers), 1)
                reloaded = loaded_layers[0]
                fields = reloaded.fields()
                self.assertEqual(
                    reloaded.editorWidgetSetup(fields.lookupField("HCODE2")).type(),
                    "ValueMap",
                )
                self.assertTrue(
                    reloaded.editFormConfig().readOnly(fields.lookupField("分類コード"))
                )
        finally:
            # removeMapLayers 後は layer / reloaded に触らない（QGIS側で破棄される）
            project.removeMapLayers([layer.id()] + loaded_ids)

        self.assertIn("<fieldConfiguration", content)
        self.assertIn('type="ValueMap"', content)
        self.assertIn("<defaults>", content)
        self.assertIn("left(", content)
        self.assertIn("<editable>", content)
