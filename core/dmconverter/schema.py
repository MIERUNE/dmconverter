"""GeoPackageレイヤスキーマ定義

要素タイプ・フィールド定義など、レイヤの構成に関する定数を定義する。
"""

from __future__ import annotations

from qgis.core import Qgis
from qgis.PyQt.QtCore import QMetaType

from .writer.geometry import (
    to_arc_geometry,
    to_circle_geometry,
    to_line_geometry,
    to_point_geometry,
    to_polygon_geometry,
)

# 要素タイプ → (ジオメトリタイプ名, WKBタイプ, ジオメトリ変換関数)
ELEMENT_TYPE_MAP = {
    "E1": ("面", Qgis.WkbType.Polygon, to_polygon_geometry),
    "E2": ("線", Qgis.WkbType.LineString, to_line_geometry),
    "E3": ("円", Qgis.WkbType.Polygon, to_circle_geometry),
    "E4": ("円弧", Qgis.WkbType.LineString, to_arc_geometry),
    "E5": ("点", Qgis.WkbType.Point, to_point_geometry),
    "E6": ("方向", Qgis.WkbType.Point, to_point_geometry),
    "E7": ("注記", Qgis.WkbType.Point, to_point_geometry),
}

# ParsedElement属性名 → GeoPackageフィールド名（DM仕様書の正式名称）
FIELD_DEFS: list[tuple[str, str, QMetaType.Type]] = [
    ("element_type", "レコードタイプ", QMetaType.Type.QString),
    ("dm_code", "分類コード", QMetaType.Type.QString),
    ("chiiki_bunrui", "地域分類", QMetaType.Type.Int),
    ("jouhou_bunrui", "情報分類", QMetaType.Type.Int),
    ("element_id", "要素識別番号", QMetaType.Type.Int),
    ("hierarchy", "階層レベル", QMetaType.Type.Int),
    ("zukei_kubun", "図形区分", QMetaType.Type.Int),
    ("data_kubun", "実データ区分", QMetaType.Type.Int),
    ("seido_kubun", "精度区分", QMetaType.Type.Int),
    ("chuki_kubun", "注記区分", QMetaType.Type.Int),
    ("teni", "転位区分", QMetaType.Type.Int),
    ("kandan", "間断区分", QMetaType.Type.Int),
    ("attribute_value", "属性数値", QMetaType.Type.Int),
    ("zokusei_kubun", "属性区分", QMetaType.Type.Int),
    ("acquired_date", "取得年月", QMetaType.Type.QString),
    ("updated_date", "更新取得年月", QMetaType.Type.QString),
    ("deleted_date", "消去年月", QMetaType.Type.QString),
]

# 注記固有フィールド（E7のみ）
ANNOTATION_FIELD_DEFS: list[tuple[str, str, QMetaType.Type]] = [
    ("text", "注記内容", QMetaType.Type.QString),
    ("orientation", "縦横区分", QMetaType.Type.Int),
    ("size", "字の大きさ", QMetaType.Type.Int),
    ("spacing", "字隔", QMetaType.Type.Int),
    ("angle", "文字列の方向", QMetaType.Type.Int),
    ("line_weight", "線号", QMetaType.Type.Int),
]

# 方向固有フィールド（E6のみ）
DIRECTION_FIELD_DEFS: list[tuple[str, QMetaType.Type]] = [
    ("方向角", QMetaType.Type.Double),
]
