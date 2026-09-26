"""レイヤスタイル設定

レイヤにラベル表示などのスタイルを適用する。
QMLのレンダラーと属性フォーム設定の適用、QLRファイルのエクスポートも行う。
"""

from __future__ import annotations

import os
from typing import NamedTuple

from qgis.core import (
    Qgis,
    QgsFeatureRenderer,
    QgsLayerDefinition,
    QgsMapLayer,
    QgsNullSymbolRenderer,
    QgsPalLayerSettings,
    QgsProperty,
    QgsReadWriteContext,
    QgsRenderContext,
    QgsRuleBasedRenderer,
    QgsSymbolLayer,
    QgsTextFormat,
    QgsUnitTypes,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
    QgsWkbTypes,
)
from qgis.PyQt.QtXml import QDomDocument, QDomElement

# QMLのシンボルタイプ → QgsWkbTypes.GeometryType の対応
_QML_SYMBOL_TO_GEOM_TYPE: dict[str, QgsWkbTypes.GeometryType] = {
    "marker": QgsWkbTypes.PointGeometry,
    "line": QgsWkbTypes.LineGeometry,
    "fill": QgsWkbTypes.PolygonGeometry,
}

# QMLから属性フォーム関連の設定だけを取り込むためのスタイルカテゴリ
#   Fields: fieldConfiguration / aliases / defaults / constraints / constraintExpressions
#   Forms:  editable / labelOnTop / reuseLastValue など editFormConfig 一式
# レンダラー・ラベル・レイヤ描画設定には影響しない
_FORM_STYLE_CATEGORIES = (
    QgsMapLayer.StyleCategory.Fields | QgsMapLayer.StyleCategory.Forms
)


class QmlStyle(NamedTuple):
    """QMLから読み込んだスタイル一式（ジオメトリタイプごとにキャッシュする）。

    Attributes:
        renderer: QMLから複製したレンダラー
        document: パース済みQML。属性フォーム設定の適用に使う
    """

    renderer: QgsFeatureRenderer
    document: QDomDocument


# build_style_cache() の戻り値。ジオメトリタイプ別のQMLスタイル
StyleCache = dict[QgsWkbTypes.GeometryType, QmlStyle]


def apply_annotation_labels(layer: QgsVectorLayer) -> None:
    """E7注記レイヤにラベル表示設定を適用する。

    DMレコードの注記属性を使い、QGISラベルとして表示する:
        - 注記内容 → ラベルテキスト
        - 字の大きさ → フォントサイズ（0.1mm→mm変換）
        - 文字列の方向 → 回転角度（縦横区分に応じて補正）
        - 縦横区分 → テキストの向き（横書き/縦書き）
        - 字隔 → 文字間隔（0.1mm→mm変換）
    """
    text_format = QgsTextFormat()
    text_format.setSizeUnit(QgsUnitTypes.RenderMillimeters)
    text_format.setSize(1.0)  # デフォルトサイズ（data-definedで上書き）
    text_format.setOrientation(Qgis.TextOrientation.Horizontal)

    settings = QgsPalLayerSettings()
    # 縦書き時のみ伸ばし棒・括弧を縦書き用文字に置換（表示のみ、データは変わらない）
    settings.isExpression = True
    settings.fieldName = (
        'CASE WHEN "縦横区分" = 1'
        " THEN replace(replace(replace(\"注記内容\", 'ー', '｜'), '（', '︵'), '）', '︶')"
        ' ELSE "注記内容"'
        " END"
    )
    settings.setFormat(text_format)

    # 字の大きさ: 0.1mm単位 → mm変換（÷10）
    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.Size,
        QgsProperty.fromExpression('"字の大きさ" / 10'),
    )

    # 文字列の方向: DM（反時計回り正）→ QGIS（時計回り正）
    # 横書き: 符号反転のみ
    # 縦書き: -90°を基準にオフセットを取り符号反転
    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.LabelRotation,
        QgsProperty.fromExpression(
            "CASE"
            ' WHEN "縦横区分" = 1 THEN -("文字列の方向" + 90)'
            ' ELSE -"文字列の方向"'
            " END"
        ),
    )

    # 縦横区分: 0=横書き, 1=縦書き
    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.TextOrientation,
        QgsProperty.fromExpression(
            "CASE WHEN \"縦横区分\" = 1 THEN 'vertical' ELSE 'horizontal' END"
        ),
    )

    # 字隔: 0.1mm単位 → mm変換（÷10）
    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.FontLetterSpacing,
        QgsProperty.fromExpression('"字隔" / 10'),
    )

    # ラベル位置をフィーチャのジオメトリに固定
    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.PositionX,
        QgsProperty.fromExpression("x($geometry)"),
    )
    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.PositionY,
        QgsProperty.fromExpression("y($geometry)"),
    )

    # 基準点アライメント（仕様書: 横書き=左下, 縦書き=左上）
    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.Hali,
        QgsProperty.fromExpression("'left'"),
    )
    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.Vali,
        QgsProperty.fromExpression(
            "CASE WHEN \"縦横区分\" = 1 THEN 'top' ELSE 'bottom' END"
        ),
    )

    labeling = QgsVectorLayerSimpleLabeling(settings)
    layer.setLabeling(labeling)
    layer.setLabelsEnabled(True)

    # 注記の原点（ポイントシンボル）を非表示にする
    layer.setRenderer(QgsNullSymbolRenderer())


def apply_direction_rotation(layer: QgsVectorLayer) -> None:
    """E6方向レイヤのシンボルに「方向角」フィールドによる回転を設定する。

    QMLの<rotation/>が空でも、方向角フィールドを使ってシンボルを回転させる。
    direction_angle()はCCW/東=0°で計算するため、QGISのCW回転に合わせて符号反転する。
    """
    renderer = layer.renderer()
    if renderer is None:
        return
    for symbol in renderer.symbols(QgsRenderContext()):
        for i in range(symbol.symbolLayerCount()):
            sl = symbol.symbolLayer(i)
            sl.setDataDefinedProperty(
                QgsSymbolLayer.Property.PropertyAngle,
                QgsProperty.fromExpression('0 - "方向角"'),
            )
    layer.triggerRepaint()


def build_style_cache(style_folder: str, feedback=None) -> StyleCache:
    """スタイルフォルダ内のQMLを読み込み、ジオメトリタイプ別にキャッシュする。

    QMLはシンボルタイプ（marker/line/fill）でジオメトリタイプを判定し、
    ファイルごとに1回だけパースする。DOMはレイヤごとの属性フォーム設定の適用に再利用する。
    同一ジオメトリタイプのQMLが複数ある場合は、ファイル名順で最初のものを使用する。

    Args:
        style_folder: QMLファイルを置いたフォルダ
        feedback: エラー・警告出力先（省略可）

    Returns:
        {QgsWkbTypes.GeometryType: QmlStyle} の辞書
    """
    if not os.path.isdir(style_folder):
        if feedback is not None:
            feedback.reportError(f"スタイルフォルダが見つかりません: {style_folder}")
        return {}

    cache: StyleCache = {}
    for fname in sorted(os.listdir(style_folder)):
        if not fname.lower().endswith(".qml"):
            continue
        document = _parse_qml_document(os.path.join(style_folder, fname))
        if document is None:
            if feedback is not None:
                feedback.reportError(f"QMLの解析に失敗（スキップ）: {fname}")
            continue
        renderer_element = document.documentElement().firstChildElement("renderer-v2")
        geom_type = _detect_qml_geom_type(renderer_element)
        if geom_type is None:
            if feedback is not None:
                feedback.pushWarning(
                    f"{fname}: カテゴリ分類スタイルではないため適用できません"
                    " — HCODE2フィールドでカテゴリ分類されたQMLを配置してください"
                )
            continue
        if geom_type in cache:
            continue
        renderer = QgsFeatureRenderer.load(renderer_element, QgsReadWriteContext())
        if renderer is None:
            if feedback is not None:
                feedback.reportError(f"QML読み込み失敗: {fname}")
            continue
        cache[geom_type] = QmlStyle(renderer=renderer, document=document)
    return cache


def _parse_qml_document(qml_path: str) -> QDomDocument | None:
    """QMLファイルをQDomDocumentとしてパースする。

    PyQt5 の ``setContent`` はタプル、PyQt6 は真偽値相当を返すため、両方を受ける。

    Returns:
        パース済みDOM。XMLとして不正な場合はNone
    """
    document = QDomDocument()
    with open(qml_path, "rb") as f:
        result = document.setContent(f.read())
    ok = result[0] if isinstance(result, tuple) else bool(result)
    return document if ok else None


def _detect_qml_geom_type(renderer: QDomElement) -> QgsWkbTypes.GeometryType | None:
    """QMLの <renderer-v2> 要素のシンボルタイプからジオメトリタイプを検出する。

    カテゴリ分類レンダラーでない場合、またはシンボルが無い場合はNone。
    """
    if renderer.attribute("type") != "categorizedSymbol":
        return None
    symbol = renderer.firstChildElement("symbols").firstChildElement("symbol")
    return _QML_SYMBOL_TO_GEOM_TYPE.get(symbol.attribute("type"))


def apply_kandan_filter(layer: QgsVectorLayer) -> None:
    """kandan=1（間断）のフィーチャをルールベースレンダラーで非表示にする。

    カテゴリ分けレンダラーをルールベースに変換し、
    各ルールに "間断区分" = 0 フィルタを追加する。
    """
    if layer.fields().indexFromName("間断区分") == -1:
        return
    rule_renderer = QgsRuleBasedRenderer.convertFromRenderer(layer.renderer())
    if rule_renderer is None:
        return
    root = rule_renderer.rootRule()
    for rule in root.children():
        expr = rule.filterExpression()
        if expr:
            rule.setFilterExpression(f'({expr}) AND "間断区分" = 0')
        else:
            rule.setFilterExpression('"間断区分" = 0')
    layer.setRenderer(rule_renderer)
    layer.triggerRepaint()


def apply_layer_style(
    layer: QgsVectorLayer, style_cache: StyleCache, feedback=None
) -> None:
    """レイヤ1件にDM用のスタイル一式を適用する。

    注記レイヤ・方向レイヤはフィールドの有無（注記内容 / 方向角）で判定する。
    処理順は固定:
        1. 注記レイヤならラベル設定（レンダラーはNullSymbol）、それ以外はQMLのレンダラー
        2. QMLの属性フォーム設定（Fields / Forms のみ。注記・非注記とも）
           QMLにあってレイヤに存在しないフィールドの設定はQGIS側で無視される
        3. 方向レイヤならシンボルの回転
        4. 間断フィルタ（レンダラーをルールベースに変換するため最後）

    Args:
        layer: 対象レイヤ
        style_cache: build_style_cache() の戻り値。レイヤのジオメトリタイプが
            未登録ならQML由来の設定は適用しない
        feedback: 警告出力先（省略可）
    """
    fields = layer.fields()
    style = style_cache.get(layer.geometryType())

    if fields.indexFromName("注記内容") >= 0:
        apply_annotation_labels(layer)
    elif style is not None:
        layer.setRenderer(style.renderer.clone())
        layer.triggerRepaint()
    if style is not None:
        ok, msg = layer.importNamedStyle(style.document, _FORM_STYLE_CATEGORIES)
        if not ok and feedback is not None:
            feedback.pushWarning(f"属性フォーム適用失敗: {layer.name()}: {msg}")
    if fields.indexFromName("方向角") >= 0:
        apply_direction_rotation(layer)
    apply_kandan_filter(layer)


def export_qlr(nodes: list, qlr_path: str, base_path: str | None = None) -> str | None:
    """レイヤをQLRファイルにエクスポートする。
    Args:
        nodes: エクスポートするレイヤツリーノードのリスト
        qlr_path: 出力するQLRファイルのパス
        base_path: 指定した場合、QLR内のデータソースパスをこのディレクトリからの相対パスに変換する

    Returns:
        成功した場合はNone、失敗した場合はエラーメッセージ
    """
    ok = QgsLayerDefinition.exportLayerDefinition(qlr_path, nodes)
    if not ok:
        return "QLRエクスポートに失敗しました"

    if base_path is not None:
        with open(qlr_path, encoding="utf-8") as f:
            content = f.read()

        def _to_relative(abs_source: str) -> str:
            pipe_idx = abs_source.find("|")
            file_path = abs_source[:pipe_idx] if pipe_idx >= 0 else abs_source
            rest = abs_source[pipe_idx:] if pipe_idx >= 0 else ""
            if os.path.isabs(file_path):
                try:
                    return os.path.relpath(file_path, base_path) + rest
                except ValueError:
                    pass
            return abs_source

        import re

        content = re.sub(
            r"(?<=<datasource>)(.*?)(?=</datasource>)",
            lambda m: _to_relative(m.group(1)),
            content,
        )
        with open(qlr_path, "w", encoding="utf-8") as f:
            f.write(content)

    return None
