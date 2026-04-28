"""GeoPackageレイヤスキーマ定義

要素タイプ・フィールド定義など、レイヤの構成に関する定数を定義する。
"""

from __future__ import annotations

from qgis.core import QgsWkbTypes
from qgis.PyQt.QtCore import QVariant

from .writer.geometry import (
    to_arc_geometry,
    to_circle_geometry,
    to_line_geometry,
    to_point_geometry,
    to_polygon_geometry,
)

# 要素タイプ → (ジオメトリタイプ名, WKBタイプ, ジオメトリ変換関数)
ELEMENT_TYPE_MAP = {
    "E1": ("面", QgsWkbTypes.Polygon, to_polygon_geometry),
    "E2": ("線", QgsWkbTypes.LineString, to_line_geometry),
    "E3": ("円", QgsWkbTypes.Polygon, to_circle_geometry),
    "E4": ("円弧", QgsWkbTypes.LineString, to_arc_geometry),
    "E5": ("点", QgsWkbTypes.Point, to_point_geometry),
    "E6": ("方向", QgsWkbTypes.Point, to_point_geometry),
    "E7": ("注記", QgsWkbTypes.Point, to_point_geometry),
}

# ParsedElement属性名 → GeoPackageフィールド名（DM仕様書の正式名称）
FIELD_DEFS: list[tuple[str, str, QVariant.Type]] = [
    ("element_type", "レコードタイプ", QVariant.String),
    ("dm_code", "分類コード", QVariant.String),
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
ANNOTATION_FIELD_DEFS: list[tuple[str, str, QVariant.Type]] = [
    ("text", "注記内容", QVariant.String),
    ("orientation", "縦横区分", QVariant.Int),
    ("size", "字の大きさ", QVariant.Int),
    ("spacing", "字隔", QVariant.Int),
    ("angle", "文字列の方向", QVariant.Int),
    ("line_weight", "線号", QVariant.Int),
]

# 方向固有フィールド（E6のみ）
DIRECTION_FIELD_DEFS: list[tuple[str, QVariant.Type]] = [
    ("方向角", QVariant.Double),
]
