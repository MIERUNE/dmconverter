"""レイヤ分け＋GeoPackage書き出し

分類コード×ジオメトリタイプでレイヤを分割し、GeoPackageに書き出す。
レイヤ名は取得分類コード表の名称を使用する。
"""

from __future__ import annotations

import os
from collections import defaultdict

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)
from PyQt5.QtCore import QVariant

from .constants import CLASSIFICATIONS, get_classification_name
from .crs import get_epsg
from .geometry import to_line_geometry, to_point_geometry
from .parser.models import ParsedDM, ParsedElement

# 要素タイプ → (ジオメトリタイプ名, WKBタイプ, ジオメトリ変換関数)
_ELEMENT_TYPE_MAP = {
    "E2": ("線", QgsWkbTypes.LineString, to_line_geometry),
    "E5": ("点", QgsWkbTypes.Point, to_point_geometry),
}


# ParsedElement属性名 → GeoPackageフィールド名（DM仕様書の正式名称）
_FIELD_DEFS: list[tuple[str, str, QVariant.Type]] = [
    ("element_type", "レコードタイプ", QVariant.String),
    ("dm_code", "分類コード", QVariant.String),
    ("item_code", "項目", QVariant.String),
    ("chiiki_bunrui", "地域分類", QVariant.Int),
    ("jouhou_bunrui", "情報分類", QVariant.Int),
    ("element_id", "要素識別番号", QVariant.Int),
    ("hierarchy", "階層レベル", QVariant.Int),
    ("zukei_kubun", "図形区分", QVariant.Int),
    ("data_kubun", "実データ区分", QVariant.Int),
    ("seido_kubun", "精度区分", QVariant.Int),
    ("chuki_kubun", "注記区分", QVariant.Int),
    ("teni", "転位区分", QVariant.Int),
    ("kandan", "間断区分", QVariant.Int),
    ("attribute_value", "属性数値", QVariant.Int),
    ("zokusei_kubun", "属性区分", QVariant.Int),
    ("acquired_date", "取得年月", QVariant.String),
    ("updated_date", "更新取得年月", QVariant.String),
    ("deleted_date", "消去年月", QVariant.String),
]


def _build_fields() -> QgsFields:
    """レイヤの属性フィールドを定義する。"""
    fields = QgsFields()
    for _, field_name, field_type in _FIELD_DEFS:
        fields.append(QgsField(field_name, field_type))
        if field_name == "分類コード":
            fields.append(QgsField("分類名", QVariant.String))
    return fields


def _get_group_name(layer_code: str) -> str:
    """上位2桁コードからグループ名を返す。"""
    group = CLASSIFICATIONS.get(layer_code)
    if group is not None:
        return group["name"]
    return layer_code


def create_layers(dm: ParsedDM) -> list[QgsVectorLayer]:
    """ParsedDM から上位2桁グループ×ジオメトリタイプ別のメモリレイヤを作成する。"""
    epsg = get_epsg(dm.mesh_info.coordinate_system)
    crs = QgsCoordinateReferenceSystem(f"EPSG:{epsg}")

    # (layer_code, geom_type_name) → [elements]
    groups: dict[tuple[str, str], list[ParsedElement]] = defaultdict(list)

    for group in dm.groups:
        for elem in group.elements:
            type_info = _ELEMENT_TYPE_MAP.get(elem.element_type)
            if type_info is None:
                continue
            geom_type_name = type_info[0]
            layer_code = elem.dm_code[:2]
            groups[(layer_code, geom_type_name)].append(elem)

    layers: list[QgsVectorLayer] = []
    fields = _build_fields()

    for (layer_code, geom_type_name), elements in groups.items():
        type_info = _ELEMENT_TYPE_MAP[elements[0].element_type]
        wkb_type = type_info[1]
        geom_func = type_info[2]

        # レイヤ名: "道路_線" or "建物_点"
        group_name = _get_group_name(layer_code)
        layer_name = f"{group_name}_{geom_type_name}"

        # メモリレイヤ作成
        uri = f"{QgsWkbTypes.displayString(wkb_type)}?crs=EPSG:{epsg}"
        layer = QgsVectorLayer(uri, layer_name, "memory")
        layer.setCrs(crs)

        provider = layer.dataProvider()
        provider.addAttributes(fields.toList())
        layer.updateFields()

        # フィーチャ追加
        features: list[QgsFeature] = []
        for elem in elements:
            if not elem.coordinates:
                continue
            feat = QgsFeature(layer.fields())
            feat.setGeometry(geom_func(elem, dm.map_sheet))
            for attr_name, field_name, _ in _FIELD_DEFS:
                feat.setAttribute(field_name, getattr(elem, attr_name))
            name = get_classification_name(elem.dm_code)
            feat.setAttribute("分類名", None if name == elem.dm_code else name)
            features.append(feat)

        provider.addFeatures(features)
        layer.updateExtents()
        layers.append(layer)

    return layers


def save_to_geopackage(layers: list[QgsVectorLayer], output_path: str) -> None:
    """メモリレイヤをGeoPackageに書き出す。"""
    if not layers:
        return

    # 既存ファイルがあれば削除（上書き）
    if os.path.exists(output_path):
        os.remove(output_path)

    for i, layer in enumerate(layers):
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = layer.name()
        if i > 0:
            options.actionOnExistingFile = (
                QgsVectorFileWriter.CreateOrOverwriteLayer
            )

        _error, _msg, _new_fname, _new_layer = (
            QgsVectorFileWriter.writeAsVectorFormatV3(
                layer,
                output_path,
                layer.transformContext(),
                options,
            )
        )
