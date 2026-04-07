"""レイヤ分け＋GeoPackage書き出し

分類コード上位2桁でレイヤを分割し、GeoPackageに書き出す。
レイヤ名は取得分類コード表の名称を使用する。
"""

from __future__ import annotations

import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant

from ..constants import CLASSIFICATIONS, get_classification_name
from ..parser.models import MapSheetInfo, ParsedDM, ParsedElement
from .crs import get_epsg
from .geometry import to_line_geometry, to_point_geometry, to_polygon_geometry

# 要素タイプ → (ジオメトリタイプ名, WKBタイプ, ジオメトリ変換関数)
_ELEMENT_TYPE_MAP = {
    "E1": ("面", QgsWkbTypes.Polygon, to_polygon_geometry),
    "E2": ("線", QgsWkbTypes.LineString, to_line_geometry),
    "E5": ("点", QgsWkbTypes.Point, to_point_geometry),
    "E7": ("注記", QgsWkbTypes.Point, to_point_geometry),
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

# 注記固有フィールド（E7のみ）
_ANNOTATION_FIELD_DEFS: list[tuple[str, str, QVariant.Type]] = [
    ("text", "注記内容", QVariant.String),
    ("orientation", "縦横区分", QVariant.Int),
    ("size", "字の大きさ", QVariant.Int),
    ("spacing", "字隔", QVariant.Int),
    ("angle", "文字列の方向", QVariant.Int),
    ("line_weight", "線号", QVariant.Int),
]


def _build_fields() -> QgsFields:
    """レイヤの属性フィールドを定義する。"""
    fields = QgsFields()
    for _, field_name, field_type in _FIELD_DEFS:
        fields.append(QgsField(field_name, field_type))
        if field_name == "分類コード":
            fields.append(QgsField("分類名", QVariant.String))
    return fields


def _build_annotation_fields() -> QgsFields:
    """注記レイヤの属性フィールドを定義する（共通 + 注記固有）。"""
    fields = _build_fields()
    for _, field_name, field_type in _ANNOTATION_FIELD_DEFS:
        fields.append(QgsField(field_name, field_type))
    return fields


def _get_group_name(layer_code: str) -> str:
    """上位2桁コードからグループ名を返す。"""
    group = CLASSIFICATIONS.get(layer_code)
    if group is not None:
        return group["name"]
    return layer_code


def create_layers(dm: ParsedDM) -> list[QgsVectorLayer]:
    """ParsedDM から上位2桁グループのメモリレイヤを作成する。"""
    return create_merged_layers([dm]).layers


@dataclass
class MergeResult:
    """create_merged_layers の戻り値"""

    layers: list[QgsVectorLayer] = field(default_factory=list)
    geom_fail_counter: Counter = field(default_factory=Counter)
    errors: list[str] = field(default_factory=list)


def create_merged_layers(dm_list: list[ParsedDM]) -> MergeResult:
    """複数ParsedDMからレイヤをマージして作成する。

    同じ分類コード上位2桁×ジオメトリタイプのフィーチャは1つのレイヤに統合される。
    CRSは最初のParsedDMの座標系を使用する。
    各要素のジオメトリ変換にはそれぞれのファイルのmap_sheetを使用する。
    """
    if not dm_list:
        return MergeResult()

    first_dm = dm_list[0]
    epsg = get_epsg(first_dm.mesh_info.coordinate_system)
    crs = QgsCoordinateReferenceSystem(f"EPSG:{epsg}")

    # (layer_code, geom_type_name) → [(element, map_sheet)]
    groups: dict[tuple[str, str], list[tuple[ParsedElement, MapSheetInfo]]] = (
        defaultdict(list)
    )

    for dm in dm_list:
        for group in dm.groups:
            for elem in group.elements:
                type_info = _ELEMENT_TYPE_MAP.get(elem.element_type)
                if type_info is None:
                    continue
                geom_type_name = type_info[0]
                layer_code = elem.dm_code[:2]
                groups[(layer_code, geom_type_name)].append((elem, dm.map_sheet))

    layers: list[QgsVectorLayer] = []
    geom_fail_counter: Counter = Counter()
    errors: list[str] = []

    for (layer_code, geom_type_name), elem_pairs in groups.items():
        first_elem = elem_pairs[0][0]
        type_info = _ELEMENT_TYPE_MAP[first_elem.element_type]
        wkb_type = type_info[1]
        geom_func = type_info[2]

        # E7の場合は注記用フィールドを使用
        is_annotation = first_elem.element_type == "E7"
        fields = _build_annotation_fields() if is_annotation else _build_fields()

        # レイヤ名: "道路_線", "建物_点", "基準点_注記" など
        group_name = _get_group_name(layer_code)

        if group_name == geom_type_name:
            layer_name = group_name
        else:
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
        for elem, map_sheet in elem_pairs:
            if not elem.coordinates:
                continue
            try:
                geom = geom_func(elem, map_sheet)
            except Exception as e:
                geom_fail_counter[(elem.element_type, elem.dm_code)] += 1
                errors.append(
                    f"{elem.element_type} {elem.dm_code} "
                    f"要素ID={elem.element_id}: {e}"
                )
                continue
            if geom is None or geom.isEmpty():
                geom_fail_counter[(elem.element_type, elem.dm_code)] += 1
                continue
            feat = QgsFeature(layer.fields())
            feat.setGeometry(geom)
            for attr_name, field_name, _ in _FIELD_DEFS:
                feat.setAttribute(field_name, getattr(elem, attr_name))
            name = get_classification_name(elem.dm_code)
            feat.setAttribute("分類名", None if name == elem.dm_code else name)

            # 注記固有フィールドの設定（E7のみ）
            if is_annotation and elem.annotation is not None:
                for attr_name, field_name, _ in _ANNOTATION_FIELD_DEFS:
                    feat.setAttribute(field_name, getattr(elem.annotation, attr_name))

            features.append(feat)

        provider.addFeatures(features)
        layer.updateExtents()
        layers.append(layer)

    return MergeResult(
        layers=layers,
        geom_fail_counter=geom_fail_counter,
        errors=errors,
    )


def save_to_geopackage(layers: list[QgsVectorLayer], output_path: str) -> list[str]:
    """メモリレイヤをGeoPackageに書き出す。

    Returns:
        書き出しに失敗したレイヤのエラーメッセージのリスト（成功時は空リスト）
    """
    errors: list[str] = []
    if not layers:
        return errors

    # 既存ファイルがあれば削除（上書き）
    if os.path.exists(output_path):
        os.remove(output_path)

    for i, layer in enumerate(layers):
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = layer.name()
        if i > 0:
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

        _error, _msg, _new_fname, _new_layer = (
            QgsVectorFileWriter.writeAsVectorFormatV3(
                layer,
                output_path,
                layer.transformContext(),
                options,
            )
        )
        if _error != QgsVectorFileWriter.NoError:
            errors.append(f"{layer.name()}: {_msg}")

    return errors
