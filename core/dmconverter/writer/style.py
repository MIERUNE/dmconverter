"""レイヤスタイル設定

レイヤにラベル表示などのスタイルを適用する。
"""

from __future__ import annotations

from qgis.core import (
    QgsPalLayerSettings,
    QgsProperty,
    QgsTextFormat,
    QgsUnitTypes,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)


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
