"""ジオメトリ変換

解釈したデータをQGISが扱えるジオメトリに変換する。
DM形式の相対座標を絶対座標に変換し、QgsGeometryを生成する。

座標系の違い:
    DM形式: X=北方向, Y=東方向
    GIS: X=東方向(経度方向), Y=北方向(緯度方向)
    → 座標を入れ替える
"""

from __future__ import annotations

from qgis.core import QgsGeometry, QgsPointXY

from ..parser.models import Coordinate, MapSheetInfo, ParsedElement

# 座標値の単位コード → メートルへの除数
_UNIT_DIVISORS = {
    1: 1000.0,  # mm → m
    10: 100.0,  # cm → m
    999: 1.0,  # m → m
}


def _to_abs_point(coord: Coordinate, map_sheet: MapSheetInfo) -> QgsPointXY:
    """DM相対座標を絶対GIS座標に変換する。

    DM: X=北, Y=東 → GIS: X=東, Y=北 に入れ替え。
    """
    if map_sheet.coord_unit not in _UNIT_DIVISORS:
        raise ValueError(
            f"未対応の座標単位コードです: {map_sheet.coord_unit}（対応: {list(_UNIT_DIVISORS.keys())}）"
        )
    divisor = _UNIT_DIVISORS[map_sheet.coord_unit]
    gis_x = map_sheet.origin_y + coord.y / divisor
    gis_y = map_sheet.origin_x + coord.x / divisor
    return QgsPointXY(gis_x, gis_y)


def to_polygon_geometry(element: ParsedElement, map_sheet: MapSheetInfo) -> QgsGeometry:
    """E1要素からPolygon geometryを生成する。"""
    points = [_to_abs_point(c, map_sheet) for c in element.coordinates]
    return QgsGeometry.fromPolygonXY([points])


def to_line_geometry(element: ParsedElement, map_sheet: MapSheetInfo) -> QgsGeometry:
    """E2要素からLineString geometryを生成する。"""
    points = [_to_abs_point(c, map_sheet) for c in element.coordinates]
    return QgsGeometry.fromPolylineXY(points)


def to_point_geometry(element: ParsedElement, map_sheet: MapSheetInfo) -> QgsGeometry:
    """E5要素からPoint geometryを生成する。"""
    point = _to_abs_point(element.coordinates[0], map_sheet)
    return QgsGeometry.fromPointXY(point)
