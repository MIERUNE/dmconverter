"""レイヤ分け＋GeoPackage書き出し

分類コード上位2桁でレイヤを分割し、GeoPackageに書き出す。
レイヤ名は取得分類コード表の名称を使用する。
"""

from __future__ import annotations

import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant

from ..constants import CLASSIFICATIONS, get_classification_name
from ..parser.models import MapSheetInfo, ParsedDM, ParsedElement
from ..schema import (
    ANNOTATION_FIELD_DEFS,
    DIRECTION_FIELD_DEFS,
    ELEMENT_TYPE_MAP,
    FIELD_DEFS,
)
from .crs import get_epsg
from .geometry import direction_angle, group_ring_polygons, to_ring_polygon_geometry


def _build_fields() -> QgsFields:
    """レイヤの属性フィールドを定義する。"""
    fields = QgsFields()
    for _, field_name, field_type in FIELD_DEFS:
        fields.append(QgsField(field_name, field_type))
        if field_name == "分類コード":
            fields.append(QgsField("分類名", QVariant.String))
            fields.append(QgsField("HCODE2", QVariant.String))
    return fields


def _build_annotation_fields() -> QgsFields:
    """注記レイヤの属性フィールドを定義する（共通 + 注記固有）。"""
    fields = _build_fields()
    for _, field_name, field_type in ANNOTATION_FIELD_DEFS:
        fields.append(QgsField(field_name, field_type))
    return fields


def _build_direction_fields() -> QgsFields:
    """方向レイヤの属性フィールドを定義する（共通 + 方向固有）。"""
    fields = _build_fields()
    for field_name, field_type in DIRECTION_FIELD_DEFS:
        fields.append(QgsField(field_name, field_type))
    return fields


def _get_layer_name(layer_code: str) -> str:
    """4桁分類コードからレイヤ名を返す。"""
    parent_code = layer_code[:2]
    data_code = layer_code[2:]
    group = CLASSIFICATIONS.get(parent_code)
    if group is None:
        return layer_code
    if data_code == "00":
        return group["name"]
    data_name = group.get(data_code)
    if data_name is None:
        return layer_code
    return data_name


def create_layers(dm: ParsedDM) -> list[QgsVectorLayer]:
    """ParsedDM から4桁コード単位のメモリレイヤを作成する。"""
    return create_merged_layers([dm]).layers


@dataclass
class MergeResult:
    """create_merged_layers の戻り値"""

    layers: list[QgsVectorLayer] = field(default_factory=list)
    geom_fail_counter: Counter = field(default_factory=Counter)
    errors: list[str] = field(default_factory=list)
    layer_parent_codes: dict[str, str] = field(default_factory=dict)
    layer_element_types: dict[str, str] = field(default_factory=dict)


def create_merged_layers(dm_list: list[ParsedDM]) -> MergeResult:
    """複数ParsedDMからレイヤをマージして作成する。

    同じ分類コード4桁×ジオメトリタイプのフィーチャは1つのレイヤに統合される。
    CRSは最初のParsedDMの座標系を使用する。
    各要素のジオメトリ変換にはそれぞれのファイルのmap_sheetを使用する。
    """
    if not dm_list:
        return MergeResult()

    first_dm = dm_list[0]
    if first_dm.mesh_info.coordinate_system is not None:
        epsg = get_epsg(first_dm.mesh_info.coordinate_system)
        crs = QgsCoordinateReferenceSystem(f"EPSG:{epsg}")
    else:
        crs = QgsCoordinateReferenceSystem()  # CRS未設定

    # (layer_code, geom_type_name) → [(element, map_sheet)]
    groups: dict[tuple[str, str], list[tuple[ParsedElement, MapSheetInfo]]] = (
        defaultdict(list)
    )

    for dm in dm_list:
        for group in dm.groups:
            for elem in group.elements:
                type_info = ELEMENT_TYPE_MAP.get(elem.element_type)
                if type_info is None:
                    continue
                geom_type_name = type_info[0]
                layer_code = elem.dm_code
                groups[(layer_code, geom_type_name)].append((elem, dm.map_sheet))

    layers: list[QgsVectorLayer] = []
    geom_fail_counter: Counter = Counter()
    errors: list[str] = []
    layer_parent_codes: dict[str, str] = {}
    layer_element_types: dict[str, str] = {}

    # 衝突するレイヤ名を事前検出
    _name_counts: Counter = Counter()
    for layer_code, geom_type_name in groups:
        g = _get_layer_name(layer_code)
        _name_counts[g if g == geom_type_name else f"{g}_{geom_type_name}"] += 1
    _conflicting_names: set[str] = {n for n, c in _name_counts.items() if c > 1}

    for (layer_code, geom_type_name), elem_pairs in groups.items():
        first_elem = elem_pairs[0][0]
        type_info = ELEMENT_TYPE_MAP[first_elem.element_type]
        wkb_type = type_info[1]
        geom_func = type_info[2]

        # 要素タイプ別フィールド
        is_annotation = first_elem.element_type == "E7"
        is_direction = first_elem.element_type == "E6"
        if is_annotation:
            fields = _build_annotation_fields()
        elif is_direction:
            fields = _build_direction_fields()
        else:
            fields = _build_fields()

        # レイヤ名: "道路_線", "建物_点", "基準点_注記" など
        data_name = _get_layer_name(layer_code)

        if data_name == geom_type_name:
            layer_name = data_name
        else:
            layer_name = f"{data_name}_{geom_type_name}"

        # 衝突する場合は親グループ名をプレフィックスに付けて一意化
        # 例: "方位_線" → "応用測量整飾_方位_線" / "測量記録等_方位_線"
        # 同一親グループ内で衝突する場合はさらに4桁コードをサフィックスに付ける
        # 例: "測量記録等_測点名称_注記" → "測量記録等_測点名称_注記_8221"
        if layer_name in _conflicting_names:
            parent_name = CLASSIFICATIONS.get(layer_code[:2], {}).get(
                "name", layer_code[:2]
            )
            layer_name = f"{parent_name}_{layer_name}"
        if layer_name in layer_parent_codes:
            layer_name = f"{layer_name}_{layer_code}"

        # メモリレイヤ作成（CRS未設定の場合はURIにcrsを含めず、setCrsで設定）
        uri = QgsWkbTypes.displayString(wkb_type)
        layer = QgsVectorLayer(uri, layer_name, "memory")
        layer.setCrs(crs)

        provider = layer.dataProvider()
        provider.addAttributes(fields.toList())
        layer.updateFields()

        # フィーチャ追加
        # 面(E1)に中庭線（内輪, zukei_kubun=31）が含まれる場合はリングポリゴンに変換する
        features: list[QgsFeature] = []
        ring_groups = group_ring_polygons(elem_pairs) if geom_type_name == "面" else []

        # (elem, geom) ペアのリストを構築
        elem_geom_pairs: list[tuple[ParsedElement, QgsGeometry]] = []
        if ring_groups:
            for outer_elem, outer_ms, inner_elems in ring_groups:
                try:
                    geom = (
                        to_ring_polygon_geometry(outer_elem, outer_ms, inner_elems)
                        if inner_elems
                        else geom_func(outer_elem, outer_ms)
                    )
                except Exception as e:
                    geom_fail_counter[
                        (outer_elem.element_type, outer_elem.dm_code)
                    ] += 1
                    errors.append(
                        f"{outer_elem.element_type} {outer_elem.dm_code} "
                        f"要素ID={outer_elem.element_id}: {e}"
                    )
                    continue
                if geom is None or geom.isEmpty():
                    geom_fail_counter[
                        (outer_elem.element_type, outer_elem.dm_code)
                    ] += 1
                    continue
                elem_geom_pairs.append((outer_elem, geom))
        else:
            for elem, map_sheet in elem_pairs:
                if not elem.coordinates:
                    continue
                if is_direction and len(elem.coordinates) > 2:
                    # E6で座標ペアが複数ある場合: ペアごとに複数フィーチャを生成
                    coords = elem.coordinates
                    for i in range(0, len(coords) - 1, 2):
                        pair_elem = replace(elem, coordinates=coords[i : i + 2])
                        try:
                            geom = geom_func(pair_elem, map_sheet)
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
                        elem_geom_pairs.append((pair_elem, geom))
                else:
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
                    elem_geom_pairs.append((elem, geom))

        for elem, geom in elem_geom_pairs:
            feat = QgsFeature(layer.fields())
            feat.setGeometry(geom)
            for attr_name, field_name, _ in FIELD_DEFS:
                feat.setAttribute(field_name, getattr(elem, attr_name))
            name = get_classification_name(elem.dm_code)
            feat.setAttribute("分類名", None if name == elem.dm_code else name)
            feat.setAttribute("HCODE2", elem.dm_code + f"{elem.zukei_kubun:02d}")

            # 注記固有フィールドの設定（E7のみ）
            if is_annotation and elem.annotation is not None:
                for attr_name, field_name, _ in ANNOTATION_FIELD_DEFS:
                    feat.setAttribute(field_name, getattr(elem.annotation, attr_name))

            # 方向固有フィールドの設定（E6のみ）
            if is_direction:
                for field_name, _ in DIRECTION_FIELD_DEFS:
                    feat.setAttribute(field_name, direction_angle(elem))

            features.append(feat)

        provider.addFeatures(features)
        layer.updateExtents()
        layers.append(layer)
        layer_parent_codes[layer_name] = layer_code[:2]
        layer_element_types[layer_name] = first_elem.element_type

    return MergeResult(
        layers=layers,
        geom_fail_counter=geom_fail_counter,
        errors=errors,
        layer_parent_codes=layer_parent_codes,
        layer_element_types=layer_element_types,
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
