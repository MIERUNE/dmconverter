"""レイヤ分け＋GeoPackage書き出し

分類コード（4桁 / 上位2桁 / 分けない）× ジオメトリ種別でレイヤを分割し、GeoPackageに書き出す。
レイヤ名は取得分類コード表の名称を使用する。
"""

from __future__ import annotations

import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from typing import Literal

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

# レイヤ分割の粒度。code4=分類コード4桁, code2=上位2桁, none=分類コードで分けない
LayerGranularity = Literal["code4", "code2", "none"]

# (内部キー, UI表示名)。順序は Processing の Enum パラメータのインデックスに対応する
LAYER_GRANULARITY_OPTIONS: tuple[tuple[LayerGranularity, str], ...] = (
    ("code4", "分類コード4桁"),
    ("code2", "分類コード2桁"),
    ("none", "分類コードで分けない"),
)
DEFAULT_LAYER_GRANULARITY: LayerGranularity = "code4"


def _layer_code(dm_code: str, granularity: LayerGranularity) -> str:
    """粒度に応じたレイヤ分割キーを返す。

    Args:
        dm_code: 4桁分類コード
        granularity: レイヤ分割の粒度

    Returns:
        code4 → 4桁コードそのまま、code2 → 上位2桁、none → 空文字

    Raises:
        ValueError: 未知の粒度が渡された場合
    """
    if granularity == "code4":
        return dm_code
    if granularity == "code2":
        return dm_code[:2]
    if granularity == "none":
        return ""
    raise ValueError(f"未知のレイヤ分割粒度です: {granularity!r}")


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
    """レイヤ分割キーからレイヤ名の分類部分を返す。

    Args:
        layer_code: _layer_code() が返す分割キー（4桁 / 2桁 / 空文字）

    Returns:
        4桁: データ名（"00" はグループ名）。コード表にない場合はコードそのまま
        2桁: グループ名。コード表にない場合はコードそのまま
        空文字: 空文字（レイヤ名はジオメトリ種別名だけになる）
    """
    if not layer_code:
        return ""
    parent_code = layer_code[:2]
    group = CLASSIFICATIONS.get(parent_code)
    if group is None:
        return layer_code
    if len(layer_code) == 2:
        return group["name"]
    data_code = layer_code[2:]
    if data_code == "00":
        return group["name"]
    data_name = group.get(data_code)
    if data_name is None:
        return layer_code
    return data_name


def _compose_layer_name(data_name: str, geom_type_name: str) -> str:
    """分類部分とジオメトリ種別名からレイヤ名を組み立てる。

    分類部分が空、またはジオメトリ種別名と同じ場合はジオメトリ種別名だけを返す。
    例: ("道路縁(街区線)", "線") → "道路縁(街区線)_線"
        ("注記", "注記") → "注記"
        ("", "面") → "面"
    """
    if not data_name or data_name == geom_type_name:
        return geom_type_name
    return f"{data_name}_{geom_type_name}"


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


def create_merged_layers(
    dm_list: list[ParsedDM],
    granularity: LayerGranularity = DEFAULT_LAYER_GRANULARITY,
) -> MergeResult:
    """複数ParsedDMからレイヤをマージして作成する。

    同じ分割キー×ジオメトリタイプのフィーチャは1つのレイヤに統合される。
    分割キーは granularity で決まる（code4: 分類コード4桁 / code2: 上位2桁 / none: 分けない）。
    CRSは最初のParsedDMの座標系を使用する。
    各要素のジオメトリ変換にはそれぞれのファイルのmap_sheetを使用する。

    Args:
        dm_list: 解析済みDMのリスト
        granularity: レイヤ分割の粒度

    Returns:
        MergeResult。layer_parent_codes の値は上位2桁（none のときは空文字＝サブグループなし）

    Raises:
        ValueError: 未知の粒度が渡された場合
    """
    if granularity not in {key for key, _ in LAYER_GRANULARITY_OPTIONS}:
        raise ValueError(f"未知のレイヤ分割粒度です: {granularity!r}")
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
                layer_code = _layer_code(elem.dm_code, granularity)
                groups[(layer_code, geom_type_name)].append((elem, dm.map_sheet))

    layers: list[QgsVectorLayer] = []
    geom_fail_counter: Counter = Counter()
    errors: list[str] = []
    layer_parent_codes: dict[str, str] = {}

    # 衝突するレイヤ名を事前検出
    _name_counts: Counter = Counter()
    for layer_code, geom_type_name in groups:
        _name_counts[
            _compose_layer_name(_get_layer_name(layer_code), geom_type_name)
        ] += 1
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

        # レイヤ名: "道路縁(街区線)_線"（4桁）, "道路_線"（2桁）, "線"（分けない）など
        data_name = _get_layer_name(layer_code)
        layer_name = _compose_layer_name(data_name, geom_type_name)

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
                    if len(coords) % 2 != 0:
                        errors.append(
                            f"{elem.element_type} {elem.dm_code} "
                            f"要素ID={elem.element_id}: "
                            "座標数が奇数のため末尾1点を無視します"
                        )
                    for i in range(0, len(coords) - 1, 2):
                        pair_coords = coords[i : i + 2]
                        pair_index = (i // 2) + 1
                        pair_elem = replace(elem, coordinates=pair_coords)
                        try:
                            geom = geom_func(pair_elem, map_sheet)
                        except Exception as e:
                            geom_fail_counter[(elem.element_type, elem.dm_code)] += 1
                            errors.append(
                                f"{elem.element_type} {elem.dm_code} "
                                f"要素ID={elem.element_id} "
                                f"pair #{pair_index} 座標={pair_coords}: {e}"
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

    return MergeResult(
        layers=layers,
        geom_fail_counter=geom_fail_counter,
        errors=errors,
        layer_parent_codes=layer_parent_codes,
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
