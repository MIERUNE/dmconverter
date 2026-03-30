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

from core.dmconverter.constants import get_classification_name
from core.dmconverter.crs import get_epsg
from core.dmconverter.geometry import to_line_geometry, to_point_geometry
from core.dmconverter.parser.models import ParsedDM, ParsedElement

# 要素タイプ → (ジオメトリタイプ名, WKBタイプ, ジオメトリ変換関数)
_ELEMENT_TYPE_MAP = {
    "E2": ("線", QgsWkbTypes.LineString, to_line_geometry),
    "E5": ("点", QgsWkbTypes.Point, to_point_geometry),
}


def _build_fields() -> QgsFields:
    """レイヤの属性フィールドを定義する。"""
    fields = QgsFields()
    fields.append(QgsField("dm_code", QVariant.String))
    fields.append(QgsField("element_type", QVariant.String))
    fields.append(QgsField("hierarchy", QVariant.Int))
    return fields


def create_layers(dm: ParsedDM) -> list[QgsVectorLayer]:
    """ParsedDM から分類コード×ジオメトリタイプ別のメモリレイヤを作成する。"""
    epsg = get_epsg(dm.index.coordinate_system)
    crs = QgsCoordinateReferenceSystem(f"EPSG:{epsg}")

    # (dm_code, geom_type_name) → [elements]
    groups: dict[tuple[str, str], list[ParsedElement]] = defaultdict(list)

    for group in dm.groups:
        for elem in group.elements:
            type_info = _ELEMENT_TYPE_MAP.get(elem.element_type)
            if type_info is None:
                continue
            geom_type_name = type_info[0]
            groups[(elem.dm_code, geom_type_name)].append(elem)

    layers: list[QgsVectorLayer] = []
    fields = _build_fields()

    for (dm_code, geom_type_name), elements in groups.items():
        type_info = _ELEMENT_TYPE_MAP[elements[0].element_type]
        wkb_type = type_info[1]
        geom_func = type_info[2]

        # レイヤ名: "道路縁（街区線）_線" or "2199_線"
        class_name = get_classification_name(dm_code)
        layer_name = f"{class_name}_{geom_type_name}"

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
            feat.setAttribute("dm_code", elem.dm_code)
            feat.setAttribute("element_type", elem.element_type)
            feat.setAttribute("hierarchy", elem.hierarchy)
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
