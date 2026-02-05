"""Geometry conversion functions for DM files.

This module provides functions to convert DM element coordinates
to geometry representations. The functions return dict-based geometry
representations that can be converted to QGIS geometries when QGIS is available.

Element types:
    - E1: Polygon (closed area)
    - E2: Line (polyline)
    - E3: Circle (defined by 3 points)
    - E4: Arc (defined by start, middle, end points)
    - E5: Point
    - E6: Direction (point with direction vector)
    - E7: Annotation (text at point)
    - E8: Attribute (no geometry)

Functions:
    - coordinates_to_point_list: Convert Coordinate tuple to point list
    - calculate_circle_from_3_points: Calculate circle center and radius
    - create_point_geometry: Create point geometry dict
    - create_line_geometry: Create line geometry dict
    - create_polygon_geometry: Create polygon geometry dict
    - create_circle_geometry: Create circle geometry dict
    - create_arc_geometry: Create arc geometry dict
    - convert_element_to_geometry: Dispatch function for element conversion
"""

from __future__ import annotations

import math
from typing import Literal, Union

from dmconverter.dm_parser.models import Coordinate


def coordinates_to_point_list(
    coords: tuple[Coordinate, ...],
    include_z: bool = False,
) -> list[tuple[float, float] | tuple[float, float, float]]:
    """Convert Coordinate tuple to list of point tuples.

    Args:
        coords: Tuple of Coordinate objects
        include_z: Whether to include Z values in output

    Returns:
        List of (x, y) or (x, y, z) tuples
    """
    result: list[tuple[float, float] | tuple[float, float, float]] = []

    for coord in coords:
        if include_z and coord.z is not None:
            result.append((coord.x, coord.y, coord.z))
        else:
            result.append((coord.x, coord.y))

    return result


def calculate_circle_from_3_points(
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
) -> tuple[tuple[float, float], float]:
    """Calculate circle center and radius from 3 points on the circumference.

    Uses the circumcenter formula to find the center of the circle
    passing through all three points.

    Args:
        p1: First point (x, y)
        p2: Second point (x, y)
        p3: Third point (x, y)

    Returns:
        Tuple of (center, radius) where center is (x, y)

    Raises:
        ValueError: If points are collinear (no unique circle)
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3

    # Calculate the determinant to check for collinearity
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))

    if abs(d) < 1e-10:
        raise ValueError("Points are collinear, no unique circle exists")

    # Calculate circumcenter
    ux = (
        (x1 * x1 + y1 * y1) * (y2 - y3)
        + (x2 * x2 + y2 * y2) * (y3 - y1)
        + (x3 * x3 + y3 * y3) * (y1 - y2)
    ) / d

    uy = (
        (x1 * x1 + y1 * y1) * (x3 - x2)
        + (x2 * x2 + y2 * y2) * (x1 - x3)
        + (x3 * x3 + y3 * y3) * (x2 - x1)
    ) / d

    # Calculate radius
    radius = math.sqrt((x1 - ux) ** 2 + (y1 - uy) ** 2)

    return ((ux, uy), radius)


def create_point_geometry(coord: Coordinate) -> dict[str, Union[str, tuple]]:
    """Create a point geometry representation.

    Args:
        coord: Coordinate for the point

    Returns:
        Dictionary with type and coordinates
    """
    if coord.z is not None:
        coordinates = (coord.x, coord.y, coord.z)
    else:
        coordinates = (coord.x, coord.y)

    return {
        "type": "Point",
        "coordinates": coordinates,
    }


def create_line_geometry(
    coords: tuple[Coordinate, ...],
) -> dict[str, Union[str, list]]:
    """Create a line geometry representation.

    Args:
        coords: Tuple of coordinates defining the line

    Returns:
        Dictionary with type and coordinates
    """
    point_list = coordinates_to_point_list(coords)

    return {
        "type": "LineString",
        "coordinates": point_list,
    }


def create_polygon_geometry(
    coords: tuple[Coordinate, ...],
) -> dict[str, Union[str, list]]:
    """Create a polygon geometry representation.

    Args:
        coords: Tuple of coordinates defining the polygon exterior ring

    Returns:
        Dictionary with type and coordinates
    """
    point_list = coordinates_to_point_list(coords)

    # Ensure ring is closed
    if point_list and point_list[0] != point_list[-1]:
        point_list.append(point_list[0])

    return {
        "type": "Polygon",
        "coordinates": [point_list],  # Exterior ring as first element
    }


def create_circle_geometry(
    coords: tuple[Coordinate, ...],
) -> dict[str, Union[str, tuple, float, list]]:
    """Create a circle geometry representation.

    Circle is defined by 3 points on the circumference.
    Returns a dict with center, radius, and approximation as polygon.

    Args:
        coords: Tuple of 3 coordinates on the circle

    Returns:
        Dictionary with type, center, radius, and coordinates (polygon approximation)
    """
    if len(coords) < 3:
        raise ValueError("Circle requires at least 3 points")

    p1 = (coords[0].x, coords[0].y)
    p2 = (coords[1].x, coords[1].y)
    p3 = (coords[2].x, coords[2].y)

    try:
        center, radius = calculate_circle_from_3_points(p1, p2, p3)
    except ValueError:
        # Fallback for collinear points - treat as line
        return create_line_geometry(coords)

    # Create polygon approximation of circle (64 segments)
    num_segments = 64
    circle_points = []
    for i in range(num_segments + 1):
        angle = 2 * math.pi * i / num_segments
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        circle_points.append((x, y))

    return {
        "type": "Circle",
        "center": center,
        "radius": radius,
        "coordinates": [circle_points],  # Polygon approximation
    }


def create_arc_geometry(
    coords: tuple[Coordinate, ...],
) -> dict[str, Union[str, tuple, float, list]]:
    """Create an arc geometry representation.

    Arc is defined by start, middle, and end points.
    Returns a dict with center, radius, start/end angles, and line approximation.

    Args:
        coords: Tuple of 3 coordinates (start, middle, end)

    Returns:
        Dictionary with type and coordinates (line approximation)
    """
    if len(coords) < 3:
        raise ValueError("Arc requires at least 3 points")

    p1 = (coords[0].x, coords[0].y)
    p2 = (coords[1].x, coords[1].y)
    p3 = (coords[2].x, coords[2].y)

    try:
        center, radius = calculate_circle_from_3_points(p1, p2, p3)
    except ValueError:
        # Fallback for collinear points - treat as line
        return create_line_geometry(coords)

    # Calculate angles
    start_angle = math.atan2(p1[1] - center[1], p1[0] - center[0])
    mid_angle = math.atan2(p2[1] - center[1], p2[0] - center[0])
    end_angle = math.atan2(p3[1] - center[1], p3[0] - center[0])

    # Determine arc direction (clockwise or counter-clockwise)
    # based on middle point position
    def normalize_angle(a: float) -> float:
        while a < 0:
            a += 2 * math.pi
        while a >= 2 * math.pi:
            a -= 2 * math.pi
        return a

    start_angle = normalize_angle(start_angle)
    mid_angle = normalize_angle(mid_angle)
    end_angle = normalize_angle(end_angle)

    # Create line approximation of arc
    num_segments = 32
    arc_points = []

    # Determine sweep direction
    if start_angle <= end_angle:
        if start_angle <= mid_angle <= end_angle:
            # Counter-clockwise
            angles = [
                start_angle + (end_angle - start_angle) * i / num_segments
                for i in range(num_segments + 1)
            ]
        else:
            # Clockwise (go the other way)
            sweep = 2 * math.pi - (end_angle - start_angle)
            angles = [
                start_angle - sweep * i / num_segments for i in range(num_segments + 1)
            ]
    else:
        if end_angle <= mid_angle <= start_angle:
            # Clockwise
            angles = [
                start_angle - (start_angle - end_angle) * i / num_segments
                for i in range(num_segments + 1)
            ]
        else:
            # Counter-clockwise (go the other way)
            sweep = 2 * math.pi - (start_angle - end_angle)
            angles = [
                start_angle + sweep * i / num_segments for i in range(num_segments + 1)
            ]

    for angle in angles:
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        arc_points.append((x, y))

    return {
        "type": "Arc",
        "center": center,
        "radius": radius,
        "coordinates": arc_points,
    }


def convert_element_to_geometry(
    data_type: Literal["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"],
    coords: tuple[Coordinate, ...],
) -> dict[str, Union[str, tuple, float, list]]:
    """Convert element coordinates to geometry based on data type.

    This is the main dispatch function that routes to the appropriate
    geometry creation function based on the element type.

    Args:
        data_type: Element type (E1-E8)
        coords: Tuple of coordinates for the element

    Returns:
        Dictionary representation of the geometry
    """
    if data_type == "E1":
        # Polygon
        return create_polygon_geometry(coords)

    elif data_type == "E2":
        # Line
        return create_line_geometry(coords)

    elif data_type == "E3":
        # Circle
        return create_circle_geometry(coords)

    elif data_type == "E4":
        # Arc
        return create_arc_geometry(coords)

    elif data_type == "E5":
        # Point
        if coords:
            return create_point_geometry(coords[0])
        raise ValueError("E5 (Point) requires at least one coordinate")

    elif data_type == "E6":
        # Direction (point with direction)
        if len(coords) < 2:
            raise ValueError("E6 (Direction) requires at least 2 coordinates")

        # First point is location, second indicates direction
        point_geom = create_point_geometry(coords[0])

        # Calculate direction angle from first to second point
        dx = coords[1].x - coords[0].x
        dy = coords[1].y - coords[0].y
        direction = math.degrees(math.atan2(dy, dx))

        point_geom["direction"] = direction
        return point_geom

    elif data_type == "E7":
        # Annotation (text at point)
        if coords:
            return create_point_geometry(coords[0])
        raise ValueError("E7 (Annotation) requires at least one coordinate")

    elif data_type == "E8":
        # Attribute (no geometry)
        return {"type": "None"}

    else:
        raise ValueError(f"Unknown data type: {data_type}")
