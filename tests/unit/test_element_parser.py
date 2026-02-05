"""Unit tests for element record parsing functions.

TDD Red phase: Test element and header record parsing.
Requirements: 1.4, 1.5
"""

from __future__ import annotations

import unittest

from dmconverter.dm_parser.element_parser import (
    parse_element_record,
    parse_header_record,
    parse_coordinate_line,
    parse_annotation_record,
    parse_attribute_record,
)


class TestParseHeaderRecord(unittest.TestCase):
    """Tests for parse_header_record function."""

    def test_parse_header_record_basic(self) -> None:
        """Parse basic header record."""
        # H record from sample: H 1100 0   0   0 1    1    0    0    1    0    0    0    0    0    0017030000000
        line = "H 1100 0   0   0 1    1    0    0    1    0    0    0    0    0    0017030000000      "
        result = parse_header_record(line)

        self.assertEqual(result["record_type"], "H")
        self.assertIn("classification_code", result)

    def test_parse_header_record_classification_code(self) -> None:
        """Parse classification code from header record."""
        line = "H 2100 0   0   0 1  192    0    0  192    0    0    0    0    0    0017030000000      "
        result = parse_header_record(line)

        self.assertEqual(result["classification_code"], "2100")

    def test_parse_header_record_element_count(self) -> None:
        """Parse element count from header record."""
        line = "H 2100 0   0   0 1  192    0    0  192    0    0    0    0    0    0017030000000      "
        result = parse_header_record(line)

        # Element count should be parsed
        self.assertIn("element_count", result)
        self.assertGreaterEqual(result["element_count"], 0)


class TestParseElementRecord(unittest.TestCase):
    """Tests for parse_element_record function."""

    def test_parse_element_record_basic(self) -> None:
        """Parse basic element record."""
        # E record from sample: E21103 0   0   1 2 02350 00  83  14      0      0      0 0       170300000000
        line = "E21103 0   0   1 2 02350 00  83  14      0      0      0 0       170300000000      "
        result = parse_element_record(line)

        self.assertEqual(result["record_type"], "E")
        self.assertIn("classification_code", result)
        self.assertIn("data_type", result)

    def test_parse_element_record_classification_code(self) -> None:
        """Parse classification code from element record.

        Classification code is at position 2-5 (4 digits).
        For line 'E21103...', the code is '1103' (not '21103').
        """
        line = "E21103 0   0   1 2 02350 00  83  14      0      0      0 0       170300000000      "
        result = parse_element_record(line)

        # Classification code is at position 2-5 (4 digits: "1103")
        self.assertEqual(result["classification_code"], "1103")

    def test_parse_element_record_data_type(self) -> None:
        """Parse data type (E1-E8) from element record."""
        line = "E21103 0   0   1 2 02350 00  83  14      0      0      0 0       170300000000      "
        result = parse_element_record(line)

        # data_type 2 = E2 (line)
        self.assertEqual(result["data_type"], "E2")

    def test_parse_element_record_hierarchy_level(self) -> None:
        """Parse hierarchy level from element record."""
        line = "E21103 0   0   1 2 02350 00  83  14      0      0      0 0       170300000000      "
        result = parse_element_record(line)

        self.assertEqual(result["hierarchy_level"], 1)

    def test_parse_element_record_coordinate_count(self) -> None:
        """Parse coordinate count from element record."""
        line = "E21103 0   0   1 2 02350 00  83  14      0      0      0 0       170300000000      "
        result = parse_element_record(line)

        # coordinate_count = 83
        self.assertEqual(result["coordinate_count"], 83)

    def test_parse_element_record_line_count(self) -> None:
        """Parse line count from element record."""
        line = "E21103 0   0   1 2 02350 00  83  14      0      0      0 0       170300000000      "
        result = parse_element_record(line)

        # line_count = 14
        self.assertEqual(result["line_count"], 14)

    def test_parse_element_record_e1_polygon(self) -> None:
        """Parse E1 (polygon) element record.

        Data type is determined by first 2 characters (E1, E2, etc.).
        """
        # E1 record (polygon) - starts with "E1"
        line = "E13001 0   0   1 2 02350 00  10   2      0      0      0 0       170300000000      "
        result = parse_element_record(line)

        self.assertEqual(result["data_type"], "E1")
        self.assertEqual(result["classification_code"], "3001")

    def test_parse_element_record_e5_point(self) -> None:
        """Parse E5 (point) element record.

        Data type is determined by first 2 characters (E5 = point).
        """
        # E5 record (point) - starts with "E5"
        line = "E55105 0   0   1 2 02350 00   1   1      0      0      0 0       170300000000      "
        result = parse_element_record(line)

        self.assertEqual(result["data_type"], "E5")
        self.assertEqual(result["classification_code"], "5105")

    def test_parse_element_record_e7_annotation(self) -> None:
        """Parse E7 (annotation) element record."""
        line = "E71001 0   0   1 7 02350 00   1   1      0      0      0 0       170300000000      "
        result = parse_element_record(line)

        self.assertEqual(result["data_type"], "E7")


class TestParseCoordinateLine(unittest.TestCase):
    """Tests for parse_coordinate_line function."""

    def test_parse_coordinate_line_2d(self) -> None:
        """Parse 2D coordinate line."""
        # Coordinate line from sample: " 352340      0 344310   8440 331500  36510"
        line = " 352340      0 344310   8440 331500  36510 339080  77320 337260  83170      "
        result = parse_coordinate_line(line, is_3d=False)

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        # Each coordinate should be (x, y) tuple
        self.assertEqual(len(result[0]), 2)

    def test_parse_coordinate_line_extracts_values(self) -> None:
        """Parse coordinate values correctly."""
        line = " 352340      0 344310   8440 331500  36510 339080  77320 337260  83170      "
        result = parse_coordinate_line(line, is_3d=False)

        # First coordinate should be (352340, 0)
        self.assertEqual(result[0], (352340, 0))
        # Second coordinate should be (344310, 8440)
        self.assertEqual(result[1], (344310, 8440))

    def test_parse_coordinate_line_3d(self) -> None:
        """Parse 3D coordinate line."""
        line = " 100000  50000   1000 200000  60000   2000      "
        result = parse_coordinate_line(line, is_3d=True)

        self.assertIsInstance(result, list)
        # Each coordinate should be (x, y, z) tuple
        if result:
            self.assertEqual(len(result[0]), 3)


class TestParseAnnotationRecord(unittest.TestCase):
    """Tests for parse_annotation_record function."""

    def test_parse_annotation_record_basic(self) -> None:
        """Parse basic annotation record."""
        # Annotation has: orientation, direction, font_size, char_spacing, text
        line = "1 000 50 10 テスト注記                                                        "
        result = parse_annotation_record(line)

        self.assertIn("orientation", result)
        self.assertIn("direction", result)
        self.assertIn("font_size", result)
        self.assertIn("text", result)

    def test_parse_annotation_record_orientation_horizontal(self) -> None:
        """Parse horizontal orientation from annotation."""
        line = "1 000 50 10 テスト                                                            "
        result = parse_annotation_record(line)

        # 1 = horizontal
        self.assertEqual(result["orientation"], "horizontal")

    def test_parse_annotation_record_orientation_vertical(self) -> None:
        """Parse vertical orientation from annotation."""
        line = "2 000 50 10 テスト                                                            "
        result = parse_annotation_record(line)

        # 2 = vertical
        self.assertEqual(result["orientation"], "vertical")


class TestParseAttributeRecord(unittest.TestCase):
    """Tests for parse_attribute_record function."""

    def test_parse_attribute_record_basic(self) -> None:
        """Parse basic attribute record."""
        line = "KEY1=VALUE1                                                                   "
        result = parse_attribute_record(line)

        self.assertIsInstance(result, dict)
        self.assertIn("attributes", result)

    def test_parse_attribute_record_extracts_key_value(self) -> None:
        """Parse key-value pairs from attribute record."""
        line = "NAME=テスト属性                                                               "
        result = parse_attribute_record(line)

        attrs = result["attributes"]
        self.assertIsInstance(attrs, list)


if __name__ == "__main__":
    unittest.main()
