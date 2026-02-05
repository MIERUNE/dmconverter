"""Unit tests for index record parsing functions.

TDD Red phase: Test index record parsing.
Requirements: 1.2
"""

from __future__ import annotations

import unittest

from dmconverter.dm_parser.models import IndexRecord
from dmconverter.dm_parser.index_record_parser import (
    parse_index_record_a,
    parse_index_record_b,
    parse_index_record_c,
    parse_index_records,
)


class TestParseIndexRecordA(unittest.TestCase):
    """Tests for parse_index_record_a function (first line of index)."""

    def test_parse_index_record_a_basic(self) -> None:
        """Parse basic index record (a) line."""
        # Based on sample data: M 02JF711 四辻... 1000大分市...
        line = "M 02JF711 四辻                 1000大分市共用空間データ           111               "
        result = parse_index_record_a(line)

        self.assertEqual(result["record_type"], "M")
        self.assertEqual(result["map_sheet_id"], "02JF711")
        self.assertEqual(result["sheet_name"].strip(), "四辻")
        self.assertEqual(result["map_info_level"], 1000)

    def test_parse_index_record_a_extracts_organization(self) -> None:
        """Parse organization name from index record (a)."""
        line = "M 02JF711 四辻                 1000大分市共用空間データ           111               "
        result = parse_index_record_a(line)

        # Organization name should be extracted
        self.assertIn("organization_name", result)

    def test_parse_index_record_a_extracts_coordinate_system(self) -> None:
        """Parse coordinate system code from index record (a)."""
        # The coordinate system code is in the trailing numbers
        line = "M 02JF711 四辻                 1000大分市共用空間データ           111               "
        result = parse_index_record_a(line)

        # Coordinate system should be extracted (1-19)
        self.assertIn("coordinate_system", result)


class TestParseIndexRecordB(unittest.TestCase):
    """Tests for parse_index_record_b function (bounds line)."""

    def test_parse_index_record_b_bounds(self) -> None:
        """Parse coordinate bounds from index record (b)."""
        # Sample: "   7500  44000   9000  46000    10268  35428  1   9000  44000   7500  46000"
        line = "   7500  44000   9000  46000    10268  35428  1   9000  44000   7500  46000         "
        result = parse_index_record_b(line)

        # Should extract bounds as tuple (min_x, min_y, max_x, max_y)
        self.assertIn("bounds", result)
        bounds = result["bounds"]
        self.assertEqual(len(bounds), 4)

    def test_parse_index_record_b_base_coordinate(self) -> None:
        """Parse base coordinate from index record (b)."""
        line = "   7500  44000   9000  46000    10268  35428  1   9000  44000   7500  46000         "
        result = parse_index_record_b(line)

        # Should extract base_coordinate (lower-left corner for relative coordinate conversion)
        self.assertIn("base_x", result)
        self.assertIn("base_y", result)

    def test_parse_index_record_b_coordinate_unit(self) -> None:
        """Parse coordinate unit from index record (b)."""
        line = "   7500  44000   9000  46000    10268  35428  1   9000  44000   7500  46000         "
        result = parse_index_record_b(line)

        # Coordinate unit code: 1=m, 10=cm, 999=mm
        self.assertIn("coordinate_unit", result)
        self.assertEqual(result["coordinate_unit"], 1)


class TestParseIndexRecordC(unittest.TestCase):
    """Tests for parse_index_record_c function (classification codes)."""

    def test_parse_index_record_c_adjacent_sheets(self) -> None:
        """Parse adjacent map sheet IDs from index record (c)."""
        # Sample: "02JF604 02JF613                                         02JF702"
        line = "02JF604 02JF613                                         02JF702                     "
        result = parse_index_record_c(line)

        # Should extract adjacent sheet IDs as a list
        self.assertIn("adjacent_sheets", result)
        self.assertIsInstance(result["adjacent_sheets"], tuple)


class TestParseIndexRecords(unittest.TestCase):
    """Tests for parse_index_records function (combines all index lines)."""

    def test_parse_index_records_creates_index_record(self) -> None:
        """Parse multiple index record lines into IndexRecord."""
        lines = (
            "M 02JF711 四辻                 1000大分市共用空間データ           111               ",
            "   7500  44000   9000  46000    10268  35428  1   9000  44000   7500  46000         ",
            "02JF604 02JF613                                         02JF702                     ",
        )
        result = parse_index_records(lines)

        self.assertIsInstance(result, IndexRecord)

    def test_parse_index_records_sets_record_type(self) -> None:
        """IndexRecord should have record type set."""
        lines = (
            "M 02JF711 四辻                 1000大分市共用空間データ           111               ",
            "   7500  44000   9000  46000    10268  35428  1   9000  44000   7500  46000         ",
            "02JF604 02JF613                                         02JF702                     ",
        )
        result = parse_index_records(lines)

        # Based on design, record_type should be "A" for index records
        # But sample shows "M" - need to clarify specification
        self.assertEqual(result.record_type, "A")

    def test_parse_index_records_sets_coordinate_system(self) -> None:
        """IndexRecord should have coordinate system code."""
        lines = (
            "M 02JF711 四辻                 1000大分市共用空間データ           111               ",
            "   7500  44000   9000  46000    10268  35428  1   9000  44000   7500  46000         ",
            "02JF604 02JF613                                         02JF702                     ",
        )
        result = parse_index_records(lines)

        # Coordinate system should be 1-19 (Japan Plane Rectangular CS)
        self.assertGreaterEqual(result.coordinate_system, 1)
        self.assertLessEqual(result.coordinate_system, 19)

    def test_parse_index_records_sets_organization_name(self) -> None:
        """IndexRecord should have organization name."""
        lines = (
            "M 02JF711 四辻                 1000大分市共用空間データ           111               ",
            "   7500  44000   9000  46000    10268  35428  1   9000  44000   7500  46000         ",
            "02JF604 02JF613                                         02JF702                     ",
        )
        result = parse_index_records(lines)

        self.assertIsInstance(result.organization_name, str)
        self.assertTrue(len(result.organization_name) > 0)


if __name__ == "__main__":
    unittest.main()
