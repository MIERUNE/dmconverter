"""レイヤスタイル設定

レイヤにラベル表示などのスタイルを適用する。
QMLスタイルの適用とQLRファイルのエクスポートも行う。
"""

from __future__ import annotations

import os
import tempfile
import xml.etree.ElementTree as ET

from qgis.core import (
    QgsLayerDefinition,
    QgsPalLayerSettings,
    QgsProperty,
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
        - 文字列の方向 → 回転角度
    """
    text_format = QgsTextFormat()
    text_format.setSizeUnit(QgsUnitTypes.RenderMillimeters)
    text_format.setSize(1.0)  # デフォルトサイズ（data-definedで上書き）

    settings = QgsPalLayerSettings()
    settings.fieldName = "注記内容"
    settings.setFormat(text_format)

    # 字の大きさ: 0.1mm単位 → mm変換（÷10）
    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.Size,
        QgsProperty.fromExpression('"字の大きさ" / 10'),
    )

    # 文字列の方向: DM（反時計回り正）→ QGIS（時計回り正）のため符号反転
    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.LabelRotation,
        QgsProperty.fromExpression('- "文字列の方向"'),
    )

    labeling = QgsVectorLayerSimpleLabeling(settings)
    layer.setLabeling(labeling)
    layer.setLabelsEnabled(True)


def build_qml_map(style_folder: str) -> dict[QgsWkbTypes.GeometryType, tuple[str, str]]:
    """スタイルフォルダ内のQMLを読み込み、ジオメトリタイプ別にリマップしたXMLを返す。

    QMLのHCODE2（6桁）カテゴリを分類コード（上4桁）にリマップする。
    注記（E7）はプラグイン側で制御するためQMLの対象外。

    Returns:
        {QgsWkbTypes.GeometryType: (remapped_xml, filename)} の辞書
    """
    qml_map: dict[QgsWkbTypes.GeometryType, tuple[str, str]] = {}
    for fname in os.listdir(style_folder):
        if not fname.lower().endswith(".qml"):
            continue
        qml_path = os.path.join(style_folder, fname)
        geom_type, remapped_xml = _remap_qml_to_classification_code(qml_path)
        if geom_type is not None and geom_type not in qml_map:
            qml_map[geom_type] = (remapped_xml, fname)
    return qml_map


def write_qml_tempfiles(
    qml_map: dict[QgsWkbTypes.GeometryType, tuple[str, str]],
) -> dict[QgsWkbTypes.GeometryType, tuple[str, str]]:
    """QMLマップのリマップ済みXMLをtempファイルに書き出す。

    ジオメトリタイプごとに1つのtempファイルを作成する（最大3ファイル）。
    呼び出し側は処理完了後に cleanup_qml_tempfiles() で削除すること。

    Returns:
        {GeometryType: (tmp_path, filename)} の辞書
    """
    tmp_map: dict[QgsWkbTypes.GeometryType, tuple[str, str]] = {}
    for geom_type, (remapped_xml, fname) in qml_map.items():
        with tempfile.NamedTemporaryFile(
            suffix=".qml", mode="w", encoding="utf-8", delete=False
        ) as tmp:
            tmp.write(remapped_xml)
            tmp_map[geom_type] = (tmp.name, fname)
    return tmp_map


def cleanup_qml_tempfiles(
    tmp_map: dict[QgsWkbTypes.GeometryType, tuple[str, str]],
) -> None:
    """write_qml_tempfiles() で作成したtempファイルを削除する。"""
    for tmp_path, _ in tmp_map.values():
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def apply_qml_by_geom_type(
    layer: QgsVectorLayer,
    tmp_map: dict[QgsWkbTypes.GeometryType, tuple[str, str]],
    feedback=None,
) -> bool:
    """ジオメトリタイプに対応するQMLをレイヤに適用する。

    Args:
        layer: スタイルを適用するレイヤ
        tmp_map: write_qml_tempfiles() の戻り値
        feedback: QgsProcessingFeedback（任意）

    Returns:
        QMLを適用できた場合はTrue
    """
    if not tmp_map:
        return False

    geom_type = layer.geometryType()
    if geom_type not in tmp_map:
        return False

    tmp_path, fname = tmp_map[geom_type]
    load_msg, load_ok = layer.loadNamedStyle(tmp_path)

    if load_ok:
        if feedback is not None:
            feedback.pushInfo(f"QML適用: {layer.name()} ← {fname}")
    else:
        if feedback is not None:
            feedback.reportError(f"QML読み込み失敗: {layer.name()}: {load_msg}")
    return load_ok


def _remap_qml_to_classification_code(
    qml_path: str,
) -> tuple[QgsWkbTypes.GeometryType | None, str]:
    """QMLのHCODE2（6桁）カテゴリを分類コード（上4桁）にリマップする。

    QMLのシンボルタイプからジオメトリタイプを検出し、
    renderer-v2 の attr を "分類コード" に変更、
    各カテゴリの value を上4桁に切り詰める（重複は除去）。

    Returns:
        (QgsWkbTypes.GeometryType または None, リマップ後のXML文字列)
    """
    ET.register_namespace("", "")
    tree = ET.parse(qml_path)
    root = tree.getroot()

    renderer = root.find(".//renderer-v2[@type='categorizedSymbol']")
    if renderer is None:
        with open(qml_path, encoding="utf-8") as f:
            return None, f.read()

    symbol = renderer.find(".//symbols/symbol")
    geom_type = _QML_SYMBOL_TO_GEOM_TYPE.get(
        symbol.get("type", "") if symbol is not None else ""
    )

    renderer.set("attr", '"分類コード"')

    categories = renderer.find("categories")
    if categories is None:
        with open(qml_path, encoding="utf-8") as f:
            return geom_type, f.read()

    seen: set[str] = set()
    to_remove = []
    for cat in list(categories):
        remapped = cat.get("value", "")[:4]
        if remapped in seen:
            to_remove.append(cat)
        else:
            seen.add(remapped)
            cat.set("value", remapped)
    for cat in to_remove:
        categories.remove(cat)

    return geom_type, ET.tostring(root, encoding="unicode", xml_declaration=True)


def export_qlr(nodes: list, qlr_path: str) -> str | None:
    """レイヤツリーノードを1つのQLRファイルにエクスポートする。

    グループノード（QgsLayerTreeGroup）を渡すとグループ階層ごと保存される。
    QLRにはデータソースURIとスタイルが埋め込まれるため、
    次回以降はQLRを追加するだけでスタイル付きレイヤとして読み込める。

    Args:
        nodes: エクスポートするレイヤツリーノードのリスト
               （QgsLayerTreeGroup または QgsLayerTreeLayer）
        qlr_path: 出力するQLRファイルのパス

    Returns:
        成功した場合はNone、失敗した場合はエラーメッセージ
    """
    ok = QgsLayerDefinition.exportLayerDefinition(qlr_path, nodes)
    if not ok:
        return "QLRエクスポートに失敗しました"
    return None
