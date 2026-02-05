"""Unit tests for coordinate processing functions.

TDD Red phase: Test coordinate system and normalization.
Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
"""

from __future__ import annotations

import unittest

from dmconverter.dm_parser.coordinate import (
    get_geodetic_datum,
    get_epsg_code,
    normalize_coordinate_unit,
    relative_to_absolute,
    is_valid_z_coordinate,
    EPSG_JGD2011,
    EPSG_JGD2000,
)
from dmconverter.dm_parser.models import Coordinate


class TestGeodeticDatum(unittest.TestCase):
    """Tests for geodetic datum functions."""

    def test_get_datum_jgd2011(self) -> None:
        """Get JGD2011 datum from code 2."""
        datum = get_geodetic_datum(2)
        self.assertEqual(datum, "JGD2011")

    def test_get_datum_jgd2000_code_0(self) -> None:
        """Get JGD2000 datum from code 0."""
        datum = get_geodetic_datum(0)
        self.assertEqual(datum, "JGD2000")

    def test_get_datum_jgd2000_code_1(self) -> None:
        """Get JGD2000 datum from code 1."""
        datum = get_geodetic_datum(1)
        self.assertEqual(datum, "JGD2000")

    def test_get_datum_default(self) -> None:
        """Unknown code defaults to JGD2011."""
        datum = get_geodetic_datum(99)
        self.assertEqual(datum, "JGD2011")


class TestEpsgCode(unittest.TestCase):
    """Tests for EPSG code functions."""

    def test_epsg_tables_exist(self) -> None:
        """EPSG tables should be defined."""
        self.assertIsInstance(EPSG_JGD2011, dict)
        self.assertIsInstance(EPSG_JGD2000, dict)

    def test_get_epsg_jgd2011_system_1(self) -> None:
        """Get EPSG code for JGD2011 system 1."""
        epsg = get_epsg_code(1, "JGD2011")
        self.assertEqual(epsg, 6669)  # EPSG:6669

    def test_get_epsg_jgd2000_system_1(self) -> None:
        """Get EPSG code for JGD2000 system 1."""
        epsg = get_epsg_code(1, "JGD2000")
        self.assertEqual(epsg, 2443)  # EPSG:2443

    def test_get_epsg_jgd2011_system_2(self) -> None:
        """Get EPSG code for JGD2011 system 2."""
        epsg = get_epsg_code(2, "JGD2011")
        self.assertEqual(epsg, 6670)  # EPSG:6670

    def test_get_epsg_all_systems_jgd2011(self) -> None:
        """All 19 coordinate systems should have JGD2011 EPSG codes."""
        for system in range(1, 20):
            epsg = get_epsg_code(system, "JGD2011")
            self.assertIsNotNone(epsg)
            self.assertGreater(epsg, 0)


class TestCoordinateNormalization(unittest.TestCase):
    """Tests for coordinate normalization functions."""

    def test_normalize_meters(self) -> None:
        """Normalize coordinate in meters (unit=1)."""
        result = normalize_coordinate_unit(1000, 1)
        self.assertEqual(result, 1000.0)

    def test_normalize_centimeters(self) -> None:
        """Normalize coordinate in centimeters (unit=10)."""
        result = normalize_coordinate_unit(10000, 10)
        self.assertEqual(result, 100.0)  # 10000 cm = 100 m

    def test_normalize_millimeters(self) -> None:
        """Normalize coordinate in millimeters (unit=999)."""
        result = normalize_coordinate_unit(100000, 999)
        self.assertEqual(result, 100.0)  # 100000 mm = 100 m


class TestRelativeToAbsolute(unittest.TestCase):
    """Tests for relative to absolute coordinate conversion."""

    def test_relative_to_absolute_basic(self) -> None:
        """Convert relative coordinate to absolute."""
        base = Coordinate(x=10000.0, y=20000.0, z=None)
        relative = Coordinate(x=500.0, y=300.0, z=None)

        result = relative_to_absolute(relative, base)

        self.assertEqual(result.x, 10500.0)
        self.assertEqual(result.y, 20300.0)

    def test_relative_to_absolute_with_z(self) -> None:
        """Convert 3D relative coordinate to absolute."""
        base = Coordinate(x=10000.0, y=20000.0, z=0.0)
        relative = Coordinate(x=500.0, y=300.0, z=100.0)

        result = relative_to_absolute(relative, base)

        self.assertEqual(result.x, 10500.0)
        self.assertEqual(result.y, 20300.0)
        self.assertEqual(result.z, 100.0)  # Z is absolute, not added


class TestValidZCoordinate(unittest.TestCase):
    """Tests for Z coordinate validation."""

    def test_valid_z_positive(self) -> None:
        """Positive Z coordinate is valid."""
        self.assertTrue(is_valid_z_coordinate(100.0))

    def test_valid_z_zero(self) -> None:
        """Zero Z coordinate is valid."""
        self.assertTrue(is_valid_z_coordinate(0.0))

    def test_valid_z_negative(self) -> None:
        """Negative Z coordinate (below sea level) is valid."""
        self.assertTrue(is_valid_z_coordinate(-10.0))

    def test_invalid_z_none(self) -> None:
        """None Z coordinate is invalid."""
        self.assertFalse(is_valid_z_coordinate(None))

    def test_invalid_z_minus999(self) -> None:
        """Z = -999 indicates no data and is invalid."""
        self.assertFalse(is_valid_z_coordinate(-999.0))

    def test_invalid_z_minus9999(self) -> None:
        """Z = -9999 indicates no data and is invalid."""
        self.assertFalse(is_valid_z_coordinate(-9999.0))


if __name__ == "__main__":
    unittest.main()
