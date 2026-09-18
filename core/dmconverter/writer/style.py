"""レイヤスタイル設定

レイヤにラベル表示などのスタイルを適用する。
QMLスタイルの適用とQLRファイルのエクスポートも行う。
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import NamedTuple

from qgis.core import (
    Qgis,
    QgsFeatureRenderer,
    QgsLayerDefinition,
    QgsMapLayer,
    QgsNullSymbolRenderer,
    QgsPalLayerSettings,
    QgsProperty,
    QgsRenderContext,
    QgsRuleBasedRenderer,
    QgsSymbolLayer,
    QgsTextFormat,
    QgsUnitTypes,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
    QgsWkbTypes,
)
from qgis.PyQt.QtXml import QDomDocument

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


def build_qml_map(
    style_folder: str,
    feedback=None,
) -> dict[QgsWkbTypes.GeometryType, str]:
    """スタイルフォルダ内のQMLを読み込み、ジオメトリタイプ別に索引化して返す。

    QMLのシンボルタイプ（marker/line/fill）を判定し、
    ジオメトリタイプをキーにしたマップを返す。
    同一ジオメトリタイプのQMLが複数ある場合は最初に見つかったものを使用する。

    Returns:
        {QgsWkbTypes.GeometryType: qml_path} の辞書
    """
    if not os.path.isdir(style_folder):
        if feedback is not None:
            feedback.reportError(f"スタイルフォルダが見つかりません: {style_folder}")
        return {}

    qml_map: dict[QgsWkbTypes.GeometryType, str] = {}
    for fname in sorted(os.listdir(style_folder)):
        if not fname.lower().endswith(".qml"):
            continue
        qml_path = os.path.join(style_folder, fname)
        try:
            geom_type = _detect_qml_geom_type(qml_path)
        except ET.ParseError:
            if feedback is not None:
                feedback.reportError(f"QMLの解析に失敗（スキップ）: {fname}")
            continue
        if geom_type is None:
            if feedback is not None:
                feedback.pushWarning(
                    f"{fname}: カテゴリ分類スタイルではないため適用できません"
                    " — HCODE2フィールドでカテゴリ分類されたQMLを配置してください"
                )
            continue
        if geom_type not in qml_map:
            qml_map[geom_type] = qml_path
    return qml_map


def _detect_qml_geom_type(qml_path: str) -> QgsWkbTypes.GeometryType | None:
    """QMLファイルのシンボルタイプからジオメトリタイプを検出する。

    Raises:
        ET.ParseError: QMLファイルが不正なXMLの場合
    """
    tree = ET.parse(qml_path)
    root = tree.getroot()
    renderer = root.find(".//renderer-v2[@type='categorizedSymbol']")
    if renderer is None:
        return None
    symbol = renderer.find(".//symbols/symbol")
    if symbol is None:
        return None
    return _QML_SYMBOL_TO_GEOM_TYPE.get(symbol.get("type", ""))


def build_style_cache(
    qml_map: dict[QgsWkbTypes.GeometryType, str],
    feedback=None,
) -> dict[QgsWkbTypes.GeometryType, QmlStyle]:
    """QMLを1回だけパースし、レンダラーとパース済みDOMをジオメトリタイプ別にキャッシュする。

    DOMはレイヤごとの属性フォーム設定の適用（apply_qml_form）に再利用する。
    QMLファイルの読み込み・パースはジオメトリタイプごとに1回で済む。

    Args:
        qml_map: build_qml_map() の戻り値
        feedback: エラー出力先（省略可）

    Returns:
        {QgsWkbTypes.GeometryType: QmlStyle} の辞書
    """
    cache: dict[QgsWkbTypes.GeometryType, QmlStyle] = {}
    for geom_type, qml_path in qml_map.items():
        wkb_type = {
            QgsWkbTypes.PointGeometry: QgsWkbTypes.Point,
            QgsWkbTypes.LineGeometry: QgsWkbTypes.LineString,
            QgsWkbTypes.PolygonGeometry: QgsWkbTypes.Polygon,
        }.get(geom_type)
        if wkb_type is None:
            continue

        document = _parse_qml_document(qml_path)
        if document is None:
            if feedback is not None:
                feedback.reportError(
                    f"QMLの解析に失敗（スキップ）: {os.path.basename(qml_path)}"
                )
            continue

        uri = f"{QgsWkbTypes.displayString(wkb_type)}?crs=EPSG:4326"
        tmp = QgsVectorLayer(uri, "_style_cache", "memory")
        load_ok, load_msg = tmp.importNamedStyle(document)
        if load_ok:
            cache[geom_type] = QmlStyle(
                renderer=tmp.renderer().clone(), document=document
            )
        elif feedback is not None:
            feedback.reportError(f"QML読み込み失敗: {qml_path}: {load_msg}")
    return cache


def _parse_qml_document(qml_path: str) -> QDomDocument | None:
    """QMLファイルをQDomDocumentとしてパースする。

    Returns:
        パース済みDOM。XMLとして不正な場合はNone
    """
    document = QDomDocument()
    with open(qml_path, "rb") as f:
        result = document.setContent(f.read())
    # PyQt5 は (ok, errorMsg, line, column) のタプル、PyQt6 も先頭要素が成否
    ok = result[0] if isinstance(result, tuple) else bool(result)
    return document if ok else None


def apply_qml_form(
    layer: QgsVectorLayer,
    style_cache: dict[QgsWkbTypes.GeometryType, QmlStyle],
    feedback=None,
) -> bool:
    """キャッシュ済みQMLから属性フォーム設定（Fields / Forms）だけをレイヤに適用する。

    ウィジェット種別・別名・デフォルト値式・制約・編集可否・labelOnTop などを取り込む。
    レンダラーやラベル設定には影響しない。
    QMLにあってレイヤに存在しないフィールドの設定はQGIS側で無視される。

    Args:
        layer: 適用先レイヤ
        style_cache: build_style_cache() の戻り値
        feedback: 警告出力先（省略可）

    Returns:
        フォーム設定を適用できた場合はTrue
    """
    geom_type = layer.geometryType()
    if geom_type not in style_cache:
        return False

    ok, msg = layer.importNamedStyle(
        style_cache[geom_type].document, _FORM_STYLE_CATEGORIES
    )
    if not ok:
        if feedback is not None:
            feedback.pushWarning(f"属性フォーム適用失敗: {layer.name()}: {msg}")
        return False
    return True


def apply_qml_by_geom_type(
    layer: QgsVectorLayer,
    style_cache: dict[QgsWkbTypes.GeometryType, QmlStyle],
) -> bool:
    """キャッシュ済みQMLのレンダラーをレイヤに適用する。

    Args:
        layer: スタイルを適用するレイヤ
        style_cache: build_style_cache() の戻り値

    Returns:
        レンダラーを適用できた場合はTrue
    """
    geom_type = layer.geometryType()
    if geom_type not in style_cache:
        return False

    layer.setRenderer(style_cache[geom_type].renderer.clone())
    layer.triggerRepaint()
    return True


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
