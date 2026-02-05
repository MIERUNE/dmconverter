"""Unit tests for map sheet record parsing functions.

TDD Red phase: Test map sheet record parsing.
Requirements: 1.3
"""

from __future__ import annotations

import unittest

from dmconverter.dm_parser.models import Coordinate, MapSheetRecord
from dmconverter.dm_parser.map_sheet_parser import (
    parse_map_sheet_record_a,
    parse_map_sheet_record_b,
    parse_map_sheet_records,
)


class TestParseMapSheetRecordA(unittest.TestCase):
    """Tests for parse_map_sheet_record_a function."""

    def test_parse_map_sheet_record_a_basic(self) -> None:
        """Parse basic map sheet record (a) line."""
        # Based on sample data line 3
        line = "0603050811ＳｕｍｍｉｔＥｖｏｌｕｔｉｏｎ平１７九公第３３号            1000 0 0 0 0 0"
        result = parse_map_sheet_record_a(line)

        self.assertIn("survey_date", result)
        self.assertIn("software_name", result)
        self.assertIn("project_name", result)
        self.assertIn("map_info_level", result)

    def test_parse_map_sheet_record_a_extracts_survey_date(self) -> None:
        """Extract survey date from map sheet record (a)."""
        line = "0603050811ＳｕｍｍｉｔＥｖｏｌｕｔｉｏｎ平１７九公第３３号            1000 0 0 0 0 0"
        result = parse_map_sheet_record_a(line)

        # Survey date should be extracted (YYMMDD format or similar)
        self.assertIn("survey_date", result)

    def test_parse_map_sheet_record_a_extracts_map_level(self) -> None:
        """Extract map info level from map sheet record (a)."""
        line = "0603050811ＳｕｍｍｉｔＥｖｏｌｕｔｉｏｎ平１７九公第３３号            1000 0 0 0 0 0"
        result = parse_map_sheet_record_a(line)

        self.assertEqual(result["map_info_level"], 1000)


class TestParseMapSheetRecordB(unittest.TestCase):
    """Tests for parse_map_sheet_record_b function (organization line)."""

    def test_parse_map_sheet_record_b_organization(self) -> None:
        """Parse organization name from map sheet record (b)."""
        line = "株式会社パスコ                             0   0   0   0   0   0   0   0            "
        result = parse_map_sheet_record_b(line)

        self.assertIn("organization_name", result)
        self.assertIn("パスコ", result["organization_name"])


class TestParseMapSheetRecords(unittest.TestCase):
    """Tests for parse_map_sheet_records function."""

    def test_parse_map_sheet_records_creates_map_sheet_record(self) -> None:
        """Parse multiple map sheet record lines into MapSheetRecord."""
        # Use index record data for bounds info
        index_lines = (
            "M 02JF711 四辻                 1000大分市共用空間データ           111               ",
            "   7500  44000   9000  46000    10268  35428  1   9000  44000   7500  46000         ",
            "02JF604 02JF613                                         02JF702                     ",
        )
        sheet_lines = (
            "0603050811ＳｕｍｍｉｔＥｖｏｌｕｔｉｏｎ平１７九公第３３号            1000 0 0 0 0 0",
            "株式会社パスコ                             0   0   0   0   0   0   0   0            ",
        )
        result = parse_map_sheet_records(index_lines, sheet_lines)

        self.assertIsInstance(result, MapSheetRecord)

    def test_parse_map_sheet_records_sets_sheet_id(self) -> None:
        """MapSheetRecord should have sheet ID."""
        index_lines = (
            "M 02JF711 四辻                 1000大分市共用空間データ           111               ",
            "   7500  44000   9000  46000    10268  35428  1   9000  44000   7500  46000         ",
            "02JF604 02JF613                                         02JF702                     ",
        )
        sheet_lines = (
            "0603050811ＳｕｍｍｉｔＥｖｏｌｕｔｉｏｎ平１７九公第３３号            1000 0 0 0 0 0",
            "株式会社パスコ                             0   0   0   0   0   0   0   0            ",
        )
        result = parse_map_sheet_records(index_lines, sheet_lines)

        self.assertEqual(result.sheet_id, "02JF711")

    def test_parse_map_sheet_records_sets_bounds(self) -> None:
        """MapSheetRecord should have coordinate bounds."""
        index_lines = (
            "M 02JF711 四辻                 1000大分市共用空間データ           111               ",
            "   7500  44000   9000  46000    10268  35428  1   9000  44000   7500  46000         ",
            "02JF604 02JF613                                         02JF702                     ",
        )
        sheet_lines = (
            "0603050811ＳｕｍｍｉｔＥｖｏｌｕｔｉｏｎ平１７九公第３３号            1000 0 0 0 0 0",
            "株式会社パスコ                             0   0   0   0   0   0   0   0            ",
        )
        result = parse_map_sheet_records(index_lines, sheet_lines)

        self.assertEqual(result.bounds, (7500.0, 44000.0, 9000.0, 46000.0))

    def test_parse_map_sheet_records_sets_base_coordinate(self) -> None:
        """MapSheetRecord should have base coordinate for relative conversion."""
        index_lines = (
            "M 02JF711 四辻                 1000大分市共用空間データ           111               ",
            "   7500  44000   9000  46000    10268  35428  1   9000  44000   7500  46000         ",
            "02JF604 02JF613                                         02JF702                     ",
        )
        sheet_lines = (
            "0603050811ＳｕｍｍｉｔＥｖｏｌｕｔｉｏｎ平１７九公第３３号            1000 0 0 0 0 0",
            "株式会社パスコ                             0   0   0   0   0   0   0   0            ",
        )
        result = parse_map_sheet_records(index_lines, sheet_lines)

        self.assertIsInstance(result.base_coordinate, Coordinate)
        self.assertEqual(result.base_coordinate.x, 10268.0)
        self.assertEqual(result.base_coordinate.y, 35428.0)

    def test_parse_map_sheet_records_sets_coordinate_unit(self) -> None:
        """MapSheetRecord should have coordinate unit."""
        index_lines = (
            "M 02JF711 四辻                 1000大分市共用空間データ           111               ",
            "   7500  44000   9000  46000    10268  35428  1   9000  44000   7500  46000         ",
            "02JF604 02JF613                                         02JF702                     ",
        )
        sheet_lines = (
            "0603050811ＳｕｍｍｉｔＥｖｏｌｕｔｉｏｎ平１７九公第３３号            1000 0 0 0 0 0",
            "株式会社パスコ                             0   0   0   0   0   0   0   0            ",
        )
        result = parse_map_sheet_records(index_lines, sheet_lines)

        # coordinate_unit: 1=m, 10=cm, 999=mm
        self.assertEqual(result.coordinate_unit, 1)


if __name__ == "__main__":
    unittest.main()
