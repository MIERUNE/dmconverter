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

from qgis.core import QgsCircle, QgsCircularString, QgsGeometry, QgsPoint, QgsPointXY

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


def to_ring_polygon_geometry(
    outer: ParsedElement,
    outer_ms: MapSheetInfo,
    inner_rings: list[tuple[ParsedElement, MapSheetInfo]],
) -> QgsGeometry:
    """E1外輪要素と内輪要素リスト（中庭線）からリングポリゴンを生成する。

    外輪リング + 内輪リング（複数可）を fromPolygonXY に渡す。
    各要素はそれぞれの MapSheetInfo で座標変換する。
    """
    rings = [[_to_abs_point(c, outer_ms) for c in outer.coordinates]]
    for inner_elem, inner_ms in inner_rings:
        rings.append([_to_abs_point(c, inner_ms) for c in inner_elem.coordinates])
    return QgsGeometry.fromPolygonXY(rings)


def group_ring_polygons(
    elem_pairs: list[tuple[ParsedElement, MapSheetInfo]],
) -> list[tuple[ParsedElement, MapSheetInfo, list[tuple[ParsedElement, MapSheetInfo]]]]:
    """面要素リストを (外輪要素, 外輪ms, [(内輪要素, 内輪ms), ...]) にグループ化する。

    内輪（中庭線, zukei_kubun=31）と外輪を空間包含で対応付ける。
    内輪が存在しない場合は空リストを返す（呼び出し元で通常処理にフォールバック）。
    外輪に収まらなかった内輪は (inner_elem, inner_ms, []) として返す（単独ポリゴン扱い）。
    """
    inner_pairs = [(e, ms) for e, ms in elem_pairs if e.zukei_kubun == 31]
    if not inner_pairs:
        return []

    outer_pairs = [(e, ms) for e, ms in elem_pairs if e.zukei_kubun != 31]

    # 内輪のジオメトリを生成（空間包含判定用）
    inner_geoms: list[tuple[ParsedElement, MapSheetInfo, QgsGeometry]] = []
    for e, ms in inner_pairs:
        if not e.coordinates:
            continue
        inner_geoms.append((e, ms, to_polygon_geometry(e, ms)))

    result: list[
        tuple[ParsedElement, MapSheetInfo, list[tuple[ParsedElement, MapSheetInfo]]]
    ] = []
    used_indices: set[int] = set()

    for outer_elem, outer_ms in outer_pairs:
        if not outer_elem.coordinates:
            continue
        outer_geom = to_polygon_geometry(outer_elem, outer_ms)
        matched_indices = [
            idx
            for idx, (_, _, ig) in enumerate(inner_geoms)
            if not ig.isEmpty() and outer_geom.contains(ig)
        ]
        matched_inners = [
            (inner_geoms[i][0], inner_geoms[i][1]) for i in matched_indices
        ]
        used_indices.update(matched_indices)
        result.append((outer_elem, outer_ms, matched_inners))

    # 外輪に収まらなかった内輪は単独ポリゴンとして出力
    for idx, (inner_elem, inner_ms, _) in enumerate(inner_geoms):
        if idx not in used_indices:
            result.append((inner_elem, inner_ms, []))

    return result


def to_circle_geometry(element: ParsedElement, map_sheet: MapSheetInfo) -> QgsGeometry:
    """E3要素（円）からPolygon geometryを生成する。

    円周上の3点からQgsCircleで円を構築し、64セグメントのポリゴンに近似する。
    """
    if len(element.coordinates) < 3:
        return QgsGeometry()
    pts = [_to_abs_point(c, map_sheet) for c in element.coordinates[:3]]
    p1 = QgsPoint(pts[0].x(), pts[0].y())
    p2 = QgsPoint(pts[1].x(), pts[1].y())
    p3 = QgsPoint(pts[2].x(), pts[2].y())
    circle = QgsCircle.from3Points(p1, p2, p3)
    if circle.isEmpty():
        return QgsGeometry()
    return QgsGeometry(circle.toPolygon(64))


def to_arc_geometry(element: ParsedElement, map_sheet: MapSheetInfo) -> QgsGeometry:
    """E4要素（円弧）からLineString geometryを生成する。

    円弧上の始点・中間点・終点の3点からQgsCircularStringで円弧を構築し、
    セグメント化したLineStringに近似する（第41条四）。
    """
    if len(element.coordinates) < 3:
        return QgsGeometry()
    pts = [_to_abs_point(c, map_sheet) for c in element.coordinates[:3]]
    p1 = QgsPoint(pts[0].x(), pts[0].y())
    p2 = QgsPoint(pts[1].x(), pts[1].y())
    p3 = QgsPoint(pts[2].x(), pts[2].y())
    arc = QgsCircularString()
    arc.setPoints([p1, p2, p3])
    if arc.isEmpty():
        return QgsGeometry()
    return QgsGeometry(arc.segmentize())


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
