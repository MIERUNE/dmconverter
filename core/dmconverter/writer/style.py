"""レイヤスタイル設定

レイヤにラベル表示などのスタイルを適用する。
QMLスタイルの適用とQLRファイルのエクスポートも行う。
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET

from qgis.core import (
    Qgis,
    QgsLayerDefinition,
    QgsNullSymbolRenderer,
    QgsPalLayerSettings,
    QgsProperty,
    QgsRuleBasedRenderer,
    QgsTextFormat,
    QgsUnitTypes,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
    QgsWkbTypes,
)

# QMLのシンボルタイプ → QgsWkbTypes.GeometryType の対応
_QML_SYMBOL_TO_GEOM_TYPE: dict[str, QgsWkbTypes.GeometryType] = {
    "marker": QgsWkbTypes.PointGeometry,
    "line": QgsWkbTypes.LineGeometry,
    "fill": QgsWkbTypes.PolygonGeometry,
}


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


def apply_qml_by_geom_type(
    layer: QgsVectorLayer,
    qml_map: dict[QgsWkbTypes.GeometryType, str],
    feedback=None,
) -> bool:
    """ジオメトリタイプに対応するQMLをレイヤに直接適用する。

    Args:
        layer: スタイルを適用するレイヤ
        qml_map: build_qml_map() の戻り値
        feedback: QgsProcessingFeedback（任意）

    Returns:
        QMLを適用できた場合はTrue
    """
    geom_type = layer.geometryType()
    if geom_type not in qml_map:
        return False

    qml_path = qml_map[geom_type]
    load_msg, load_ok = layer.loadNamedStyle(qml_path)

    if load_ok:
        layer.triggerRepaint()
    else:
        if feedback is not None:
            feedback.reportError(f"QML読み込み失敗: {layer.name()}: {load_msg}")
    return load_ok


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


def export_qlr(nodes: list, qlr_path: str) -> str | None:
    """レイヤをQLRファイルにエクスポートする。
    Args:
        nodes: エクスポートするレイヤツリーノードのリスト
        qlr_path: 出力するQLRファイルのパス

    Returns:
        成功した場合はNone、失敗した場合はエラーメッセージ
    """
    ok = QgsLayerDefinition.exportLayerDefinition(qlr_path, nodes)
    if not ok:
        return "QLRエクスポートに失敗しました"
    return None
