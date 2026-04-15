"""レイヤスタイル設定

レイヤにラベル表示などのスタイルを適用する。
"""

from __future__ import annotations

from qgis.core import (
    Qgis,
    QgsNullSymbolRenderer,
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
