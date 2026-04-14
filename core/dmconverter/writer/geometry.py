"""ジオメトリ変換

解釈したデータをQGISが扱えるジオメトリに変換する。
DM形式の相対座標を絶対座標に変換し、QgsGeometryを生成する。

座標系の違い:
    DM形式: X=北方向, Y=東方向
    GIS: X=東方向(経度方向), Y=北方向(緯度方向)
    → 座標を入れ替える
"""

from __future__ import annotations

import math

from qgis.core import QgsCircle, QgsGeometry, QgsPoint, QgsPointXY

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


def to_circle_geometry(element: ParsedElement, map_sheet: MapSheetInfo) -> QgsGeometry:
    """E3要素（円）からPolygon geometryを生成する。

    円周上の3点からQgsCircleで円を構築し、64セグメントのポリゴンに近似する。
    """
    pts = [_to_abs_point(c, map_sheet) for c in element.coordinates[:3]]
    p1 = QgsPoint(pts[0].x(), pts[0].y())
    p2 = QgsPoint(pts[1].x(), pts[1].y())
    p3 = QgsPoint(pts[2].x(), pts[2].y())
    circle = QgsCircle.from3Points(p1, p2, p3)
    if circle.isEmpty():
        return QgsGeometry()
    return QgsGeometry(circle.toPolygon(64))


def to_line_geometry(element: ParsedElement, map_sheet: MapSheetInfo) -> QgsGeometry:
    """E2要素からLineString geometryを生成する。"""
    points = [_to_abs_point(c, map_sheet) for c in element.coordinates]
    return QgsGeometry.fromPolylineXY(points)


def to_point_geometry(element: ParsedElement, map_sheet: MapSheetInfo) -> QgsGeometry:
    """E5・E6・E7要素（点・方向・注記）からPoint geometryを生成する。"""
    point = _to_abs_point(element.coordinates[0], map_sheet)
    return QgsGeometry.fromPointXY(point)


def direction_angle(element: ParsedElement) -> float | None:
    """E6要素から方向角（度）を計算する。

    DM座標系（X=北、Y=東）でY軸（東方向）を0°基準として、
    記号位置→方向点の方位角を度数で返す（第49条第4項）。
    座標が2点未満の場合はNoneを返す。

    戻り値の例:
        +Y方向（東）: 0°
        +X方向（北）: 90°
        -Y方向（西）: ±180°
        -X方向（南）: -90°
    """
    if len(element.coordinates) < 2:
        return None
    p1 = element.coordinates[0]
    p2 = element.coordinates[1]
    dx = p2.x - p1.x  # 北成分
    dy = p2.y - p1.y  # 東成分
    return math.degrees(math.atan2(dx, dy))
