"""Unit tests for record parsing helper functions.

TDD Red phase: Test field extraction and parsing utilities.
Requirements: 1.1, 6.3, 6.5
"""

from __future__ import annotations

import unittest

from dmconverter.dm_parser.record_helpers import (
    extract_field,
    is_modification_history_record,
    parse_float,
    parse_int,
    should_skip_record,
)


class TestExtractField(unittest.TestCase):
    """Tests for extract_field function."""

    def test_extract_field_basic(self) -> None:
        """Extract field from middle of line."""
        line = "ABCDEFGHIJ"
        result = extract_field(line, 2, 5)
        self.assertEqual(result, "CDE")

    def test_extract_field_from_start(self) -> None:
        """Extract field from beginning of line."""
        line = "ABCDEFGHIJ"
        result = extract_field(line, 0, 3)
        self.assertEqual(result, "ABC")

    def test_extract_field_to_end(self) -> None:
        """Extract field to end of line."""
        line = "ABCDEFGHIJ"
        result = extract_field(line, 7, 10)
        self.assertEqual(result, "HIJ")

    def test_extract_field_with_spaces(self) -> None:
        """Extract field containing only spaces returns empty after strip."""
        line = "ABC   DEF"
        result = extract_field(line, 3, 6)
        # Spaces are stripped, so result is empty
        self.assertEqual(result, "")

    def test_extract_field_strips_whitespace(self) -> None:
        """Extract field should strip leading/trailing whitespace."""
        line = "ABC  123  DEF"
        result = extract_field(line, 3, 8)
        self.assertEqual(result, "123")

    def test_extract_field_empty_result(self) -> None:
        """Extract field with only spaces returns empty string."""
        line = "ABC     DEF"
        result = extract_field(line, 3, 8)
        self.assertEqual(result, "")

    def test_extract_field_short_line(self) -> None:
        """Extract field from line shorter than end index returns available content."""
        line = "ABCDE"
        result = extract_field(line, 3, 10)
        self.assertEqual(result, "DE")

    def test_extract_field_start_beyond_line(self) -> None:
        """Extract field with start beyond line length returns empty string."""
        line = "ABCDE"
        result = extract_field(line, 10, 15)
        self.assertEqual(result, "")

    def test_extract_field_80_byte_record(self) -> None:
        """Extract field from 80-byte DM record."""
        # Simulated 80-byte record (padded with spaces)
        line = "M 02JF711 " + " " * 70
        result = extract_field(line, 0, 1)
        self.assertEqual(result, "M")
        result = extract_field(line, 2, 10)
        self.assertEqual(result, "02JF711")


class TestParseInt(unittest.TestCase):
    """Tests for parse_int function."""

    def test_parse_int_valid_number(self) -> None:
        """Parse valid integer string."""
        result = parse_int("123")
        self.assertEqual(result, 123)

    def test_parse_int_negative(self) -> None:
        """Parse negative integer string."""
        result = parse_int("-456")
        self.assertEqual(result, -456)

    def test_parse_int_with_spaces(self) -> None:
        """Parse integer with surrounding spaces."""
        result = parse_int("  789  ")
        self.assertEqual(result, 789)

    def test_parse_int_empty_string(self) -> None:
        """Parse empty string returns default."""
        result = parse_int("")
        self.assertEqual(result, 0)

    def test_parse_int_spaces_only(self) -> None:
        """Parse spaces only returns default."""
        result = parse_int("     ")
        self.assertEqual(result, 0)

    def test_parse_int_invalid_string(self) -> None:
        """Parse invalid string returns default."""
        result = parse_int("abc")
        self.assertEqual(result, 0)

    def test_parse_int_custom_default(self) -> None:
        """Parse invalid string with custom default."""
        result = parse_int("abc", default=-1)
        self.assertEqual(result, -1)

    def test_parse_int_float_string(self) -> None:
        """Parse float string returns default (strict integer parsing)."""
        result = parse_int("12.34")
        self.assertEqual(result, 0)

    def test_parse_int_leading_zeros(self) -> None:
        """Parse integer with leading zeros."""
        result = parse_int("007")
        self.assertEqual(result, 7)


class TestParseFloat(unittest.TestCase):
    """Tests for parse_float function."""

    def test_parse_float_valid_number(self) -> None:
        """Parse valid float string."""
        result = parse_float("123.45")
        self.assertAlmostEqual(result, 123.45)

    def test_parse_float_integer_string(self) -> None:
        """Parse integer string as float."""
        result = parse_float("789")
        self.assertAlmostEqual(result, 789.0)

    def test_parse_float_negative(self) -> None:
        """Parse negative float string."""
        result = parse_float("-456.78")
        self.assertAlmostEqual(result, -456.78)

    def test_parse_float_with_spaces(self) -> None:
        """Parse float with surrounding spaces."""
        result = parse_float("  12.34  ")
        self.assertAlmostEqual(result, 12.34)

    def test_parse_float_empty_string(self) -> None:
        """Parse empty string returns default."""
        result = parse_float("")
        self.assertAlmostEqual(result, 0.0)

    def test_parse_float_spaces_only(self) -> None:
        """Parse spaces only returns default."""
        result = parse_float("     ")
        self.assertAlmostEqual(result, 0.0)

    def test_parse_float_invalid_string(self) -> None:
        """Parse invalid string returns default."""
        result = parse_float("xyz")
        self.assertAlmostEqual(result, 0.0)

    def test_parse_float_custom_default(self) -> None:
        """Parse invalid string with custom default."""
        result = parse_float("xyz", default=-1.0)
        self.assertAlmostEqual(result, -1.0)

    def test_parse_float_scientific_notation(self) -> None:
        """Parse scientific notation."""
        result = parse_float("1.5e2")
        self.assertAlmostEqual(result, 150.0)


class TestIsModificationHistoryRecord(unittest.TestCase):
    """Tests for is_modification_history_record function."""

    def test_not_modification_history_normal_record(self) -> None:
        """Normal record (history code 0) is not modification history."""
        # 80-byte record with history code 0 at position 79 (last char)
        base = "E21103 0   0   1 2 02350 00  83  14      0      0      0 0       1703000000000"
        line = base.ljust(79) + "0"  # Ensure 80 chars with '0' at end
        self.assertEqual(len(line), 80)
        self.assertFalse(is_modification_history_record(line))

    def test_is_modification_history_code_1(self) -> None:
        """Record with history code 1 is modification history."""
        # 80-byte record with history code 1 at position 79 (last char)
        base = "E21103 0   0   1 2 02350 00  83  14      0      0      0 0       1703000000000"
        line = base.ljust(79) + "1"  # Ensure 80 chars with '1' at end
        self.assertEqual(len(line), 80)
        self.assertTrue(is_modification_history_record(line))

    def test_is_modification_history_code_2(self) -> None:
        """Record with history code 2 is modification history."""
        # 80-byte record with history code 2 at position 79 (last char)
        base = "E21103 0   0   1 2 02350 00  83  14      0      0      0 0       1703000000000"
        line = base.ljust(79) + "2"  # Ensure 80 chars with '2' at end
        self.assertEqual(len(line), 80)
        self.assertTrue(is_modification_history_record(line))

    def test_not_modification_history_short_line(self) -> None:
        """Short line without history code is not modification history."""
        line = "SHORT"
        self.assertFalse(is_modification_history_record(line))

    def test_not_modification_history_index_record(self) -> None:
        """Index record (M type) is not modification history."""
        line = "M 02JF711 " + " " * 70
        self.assertFalse(is_modification_history_record(line))


class TestShouldSkipRecord(unittest.TestCase):
    """Tests for should_skip_record function."""

    def test_should_not_skip_normal_record(self) -> None:
        """Normal record should not be skipped."""
        # 80-byte record with history code 0
        base = "E21103 0   0   1 2 02350 00  83  14      0      0      0 0       1703000000000"
        line = base.ljust(79) + "0"  # Ensure 80 chars with '0' at end
        self.assertEqual(len(line), 80)
        self.assertFalse(should_skip_record(line))

    def test_should_skip_modification_history(self) -> None:
        """Modification history record should be skipped."""
        # 80-byte record with history code 1
        base = "E21103 0   0   1 2 02350 00  83  14      0      0      0 0       1703000000000"
        line = base.ljust(79) + "1"  # Ensure 80 chars with '1' at end
        self.assertEqual(len(line), 80)
        self.assertTrue(should_skip_record(line))

    def test_should_not_skip_empty_line(self) -> None:
        """Empty line should not be skipped (handled elsewhere)."""
        line = ""
        self.assertFalse(should_skip_record(line))

    def test_should_not_skip_index_record(self) -> None:
        """Index record should not be skipped."""
        line = "M 02JF711 " + " " * 70
        self.assertFalse(should_skip_record(line))


if __name__ == "__main__":
    unittest.main()
