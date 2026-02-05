"""Unit tests for geometry conversion functions.

TDD Red phase: Test geometry conversion.
Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7
"""

from __future__ import annotations

import unittest
import math

from dmconverter.dm_parser.geometry import (
    coordinates_to_point_list,
    calculate_circle_from_3_points,
    create_point_geometry,
    create_line_geometry,
    create_polygon_geometry,
    create_circle_geometry,
    create_arc_geometry,
    convert_element_to_geometry,
)
from dmconverter.dm_parser.models import Coordinate


class TestCoordinatesToPointList(unittest.TestCase):
    """Tests for coordinates_to_point_list function."""

    def test_converts_coordinates_to_list(self) -> None:
        """Convert coordinate tuple to point list."""
        coords = (
            Coordinate(x=100.0, y=200.0, z=None),
            Coordinate(x=150.0, y=250.0, z=None),
        )
        result = coordinates_to_point_list(coords)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], (100.0, 200.0))
        self.assertEqual(result[1], (150.0, 250.0))

    def test_handles_3d_coordinates(self) -> None:
        """Convert 3D coordinates includes Z value."""
        coords = (
            Coordinate(x=100.0, y=200.0, z=10.0),
            Coordinate(x=150.0, y=250.0, z=20.0),
        )
        result = coordinates_to_point_list(coords, include_z=True)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], (100.0, 200.0, 10.0))
        self.assertEqual(result[1], (150.0, 250.0, 20.0))


class TestCalculateCircle(unittest.TestCase):
    """Tests for circle calculation from 3 points."""

    def test_calculate_circle_basic(self) -> None:
        """Calculate circle center and radius from 3 points."""
        # Points on a circle centered at (0, 0) with radius 1
        p1 = (1.0, 0.0)
        p2 = (0.0, 1.0)
        p3 = (-1.0, 0.0)

        center, radius = calculate_circle_from_3_points(p1, p2, p3)

        self.assertAlmostEqual(center[0], 0.0, places=5)
        self.assertAlmostEqual(center[1], 0.0, places=5)
        self.assertAlmostEqual(radius, 1.0, places=5)

    def test_calculate_circle_arbitrary(self) -> None:
        """Calculate circle from arbitrary 3 points."""
        # Points on a circle centered at (5, 5) with radius 5
        p1 = (10.0, 5.0)  # Right
        p2 = (5.0, 10.0)  # Top
        p3 = (0.0, 5.0)  # Left

        center, radius = calculate_circle_from_3_points(p1, p2, p3)

        self.assertAlmostEqual(center[0], 5.0, places=5)
        self.assertAlmostEqual(center[1], 5.0, places=5)
        self.assertAlmostEqual(radius, 5.0, places=5)


class TestCreatePointGeometry(unittest.TestCase):
    """Tests for create_point_geometry function."""

    def test_create_point_returns_dict(self) -> None:
        """Create point geometry returns dict representation."""
        coord = Coordinate(x=100.0, y=200.0, z=None)
        result = create_point_geometry(coord)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["type"], "Point")
        self.assertEqual(result["coordinates"], (100.0, 200.0))

    def test_create_point_3d(self) -> None:
        """Create 3D point geometry."""
        coord = Coordinate(x=100.0, y=200.0, z=50.0)
        result = create_point_geometry(coord)

        self.assertEqual(result["type"], "Point")
        self.assertEqual(result["coordinates"], (100.0, 200.0, 50.0))


class TestCreateLineGeometry(unittest.TestCase):
    """Tests for create_line_geometry function."""

    def test_create_line_returns_dict(self) -> None:
        """Create line geometry returns dict representation."""
        coords = (
            Coordinate(x=0.0, y=0.0, z=None),
            Coordinate(x=100.0, y=100.0, z=None),
            Coordinate(x=200.0, y=0.0, z=None),
        )
        result = create_line_geometry(coords)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["type"], "LineString")
        self.assertEqual(len(result["coordinates"]), 3)


class TestCreatePolygonGeometry(unittest.TestCase):
    """Tests for create_polygon_geometry function."""

    def test_create_polygon_returns_dict(self) -> None:
        """Create polygon geometry returns dict representation."""
        coords = (
            Coordinate(x=0.0, y=0.0, z=None),
            Coordinate(x=100.0, y=0.0, z=None),
            Coordinate(x=100.0, y=100.0, z=None),
            Coordinate(x=0.0, y=100.0, z=None),
            Coordinate(x=0.0, y=0.0, z=None),  # Closed ring
        )
        result = create_polygon_geometry(coords)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["type"], "Polygon")


class TestCreateCircleGeometry(unittest.TestCase):
    """Tests for create_circle_geometry function."""

    def test_create_circle_returns_dict(self) -> None:
        """Create circle geometry returns dict representation."""
        # 3 points defining a circle
        coords = (
            Coordinate(x=10.0, y=5.0, z=None),  # Right
            Coordinate(x=5.0, y=10.0, z=None),  # Top
            Coordinate(x=0.0, y=5.0, z=None),  # Left
        )
        result = create_circle_geometry(coords)

        self.assertIsInstance(result, dict)
        self.assertIn("type", result)


class TestCreateArcGeometry(unittest.TestCase):
    """Tests for create_arc_geometry function."""

    def test_create_arc_returns_dict(self) -> None:
        """Create arc geometry returns dict representation."""
        # Start, middle, end points
        coords = (
            Coordinate(x=10.0, y=5.0, z=None),  # Start
            Coordinate(x=5.0, y=10.0, z=None),  # Middle
            Coordinate(x=0.0, y=5.0, z=None),  # End
        )
        result = create_arc_geometry(coords)

        self.assertIsInstance(result, dict)
        self.assertIn("type", result)


class TestConvertElementToGeometry(unittest.TestCase):
    """Tests for convert_element_to_geometry function."""

    def test_convert_e5_to_point(self) -> None:
        """Convert E5 element to point geometry."""
        coords = (Coordinate(x=100.0, y=200.0, z=None),)
        result = convert_element_to_geometry("E5", coords)

        self.assertEqual(result["type"], "Point")

    def test_convert_e2_to_line(self) -> None:
        """Convert E2 element to line geometry."""
        coords = (
            Coordinate(x=0.0, y=0.0, z=None),
            Coordinate(x=100.0, y=100.0, z=None),
        )
        result = convert_element_to_geometry("E2", coords)

        self.assertEqual(result["type"], "LineString")

    def test_convert_e1_to_polygon(self) -> None:
        """Convert E1 element to polygon geometry."""
        coords = (
            Coordinate(x=0.0, y=0.0, z=None),
            Coordinate(x=100.0, y=0.0, z=None),
            Coordinate(x=100.0, y=100.0, z=None),
            Coordinate(x=0.0, y=100.0, z=None),
            Coordinate(x=0.0, y=0.0, z=None),
        )
        result = convert_element_to_geometry("E1", coords)

        self.assertEqual(result["type"], "Polygon")

    def test_convert_e6_to_point_with_direction(self) -> None:
        """Convert E6 element to point with direction attribute."""
        coords = (
            Coordinate(x=100.0, y=200.0, z=None),
            Coordinate(x=110.0, y=210.0, z=None),  # Direction point
        )
        result = convert_element_to_geometry("E6", coords)

        self.assertEqual(result["type"], "Point")
        self.assertIn("direction", result)


if __name__ == "__main__":
    unittest.main()
