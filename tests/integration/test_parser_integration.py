"""Integration tests for DM Parser.

Tests the complete parsing pipeline using real DM files.
Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 6.1-6.6
"""

from __future__ import annotations

import os
import unittest

from dmconverter.dm_parser.api import (
    parse_dm_file,
    get_map_sheet_info,
    get_element_summary,
    get_crs_info,
)
from dmconverter.dm_parser.errors import is_success, is_failure


# Test data paths
SAMPLE_DM_SMALL = "tests/sample_data/02JF711.dm"
SAMPLE_DM_LARGE = "tests/sample_data/02JF613.dm"


class TestParserIntegrationSmallFile(unittest.TestCase):
    """Integration tests using small sample file (02JF711.dm)."""

    @classmethod
    def setUpClass(cls) -> None:
        """Parse the sample file once for all tests."""
        if os.path.exists(SAMPLE_DM_SMALL):
            cls.result = parse_dm_file(SAMPLE_DM_SMALL)
            cls.file_exists = True
        else:
            cls.file_exists = False

    def test_file_parses_successfully(self) -> None:
        """Sample file should parse without errors."""
        if not self.file_exists:
            self.skipTest("Sample file not found")
        self.assertTrue(is_success(self.result))

    def test_index_record_parsed(self) -> None:
        """Index record should be parsed correctly."""
        if not self.file_exists or not is_success(self.result):
            self.skipTest("Sample file not found or parse failed")

        dm_data = self.result.value
        index = dm_data.index

        self.assertEqual(index.record_type, "A")
        self.assertGreaterEqual(index.coordinate_system, 1)
        self.assertLessEqual(index.coordinate_system, 19)

    def test_map_sheet_parsed(self) -> None:
        """Map sheet record should be parsed correctly."""
        if not self.file_exists or not is_success(self.result):
            self.skipTest("Sample file not found or parse failed")

        dm_data = self.result.value
        self.assertGreater(len(dm_data.map_sheets), 0)

        sheet = dm_data.map_sheets[0]
        self.assertEqual(sheet.sheet_id, "02JF711")
        self.assertEqual(sheet.map_info_level, 1000)

    def test_elements_parsed(self) -> None:
        """Element records should be parsed."""
        if not self.file_exists or not is_success(self.result):
            self.skipTest("Sample file not found or parse failed")

        dm_data = self.result.value
        self.assertGreater(len(dm_data.elements), 0)

        # Count total elements
        total_elements = sum(
            len(group.elements) for group in dm_data.elements
        )
        self.assertGreater(total_elements, 0)

    def test_coordinates_parsed(self) -> None:
        """Element coordinates should be parsed."""
        if not self.file_exists or not is_success(self.result):
            self.skipTest("Sample file not found or parse failed")

        dm_data = self.result.value

        # Find an element with coordinates
        for group in dm_data.elements:
            for element in group.elements:
                if element.coordinates:
                    coord = element.coordinates[0]
                    # Coordinates should be absolute (base + relative)
                    self.assertGreater(coord.x, 0)
                    self.assertGreater(coord.y, 0)
                    return

        self.fail("No elements with coordinates found")

    def test_crs_code_valid(self) -> None:
        """CRS code should be a valid EPSG code."""
        if not self.file_exists or not is_success(self.result):
            self.skipTest("Sample file not found or parse failed")

        dm_data = self.result.value

        # Valid EPSG codes for Japan are in range 2443-2461 (JGD2000)
        # or 6669-6687 (JGD2011)
        crs = dm_data.crs_code
        valid_jgd2000 = 2443 <= crs <= 2461
        valid_jgd2011 = 6669 <= crs <= 6687

        self.assertTrue(valid_jgd2000 or valid_jgd2011)

    def test_datum_valid(self) -> None:
        """Datum should be JGD2011 or JGD2000."""
        if not self.file_exists or not is_success(self.result):
            self.skipTest("Sample file not found or parse failed")

        dm_data = self.result.value
        self.assertIn(dm_data.datum, ("JGD2011", "JGD2000"))

    def test_element_types_parsed(self) -> None:
        """Various element types should be parsed."""
        if not self.file_exists or not is_success(self.result):
            self.skipTest("Sample file not found or parse failed")

        dm_data = self.result.value
        summary = get_element_summary(dm_data)

        # Should have at least some E2 (line) elements
        self.assertIn("E2", summary)
        self.assertGreater(summary["E2"], 0)

    def test_map_sheet_info_accessor(self) -> None:
        """Map sheet info accessor should work."""
        if not self.file_exists or not is_success(self.result):
            self.skipTest("Sample file not found or parse failed")

        dm_data = self.result.value
        info = get_map_sheet_info(dm_data)

        self.assertEqual(info["sheet_id"], "02JF711")
        self.assertEqual(info["map_info_level"], 1000)
        self.assertIn("bounds", info)

    def test_crs_info_accessor(self) -> None:
        """CRS info accessor should work."""
        if not self.file_exists or not is_success(self.result):
            self.skipTest("Sample file not found or parse failed")

        dm_data = self.result.value
        info = get_crs_info(dm_data)

        self.assertIn("crs_code", info)
        self.assertIn("epsg", info)
        self.assertIn("datum", info)
        self.assertTrue(info["epsg"].startswith("EPSG:"))


class TestParserIntegrationLargeFile(unittest.TestCase):
    """Integration tests using large sample file (02JF613.dm)."""

    @classmethod
    def setUpClass(cls) -> None:
        """Parse the sample file once for all tests."""
        if os.path.exists(SAMPLE_DM_LARGE):
            cls.result = parse_dm_file(SAMPLE_DM_LARGE)
            cls.file_exists = True
        else:
            cls.file_exists = False

    def test_large_file_parses_successfully(self) -> None:
        """Large sample file should parse without errors."""
        if not self.file_exists:
            self.skipTest("Large sample file not found")
        self.assertTrue(is_success(self.result))

    def test_large_file_has_many_elements(self) -> None:
        """Large file should have many elements."""
        if not self.file_exists or not is_success(self.result):
            self.skipTest("Large sample file not found or parse failed")

        dm_data = self.result.value
        total_elements = sum(
            len(group.elements) for group in dm_data.elements
        )

        # Large file should have more elements than small file
        self.assertGreater(total_elements, 1000)


class TestParserErrorHandling(unittest.TestCase):
    """Tests for parser error handling."""

    def test_nonexistent_file_returns_failure(self) -> None:
        """Parsing nonexistent file returns Failure."""
        result = parse_dm_file("nonexistent_file.dm")
        self.assertTrue(is_failure(result))
        self.assertEqual(result.error_type, "FileNotFound")

    def test_failure_has_context(self) -> None:
        """Failure should include context information."""
        result = parse_dm_file("nonexistent_file.dm")
        self.assertTrue(is_failure(result))
        self.assertIsNotNone(result.context)
        self.assertIn("file", result.context)


if __name__ == "__main__":
    unittest.main()
