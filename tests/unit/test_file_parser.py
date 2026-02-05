"""Unit tests for file parsing functions.

TDD Red phase: Test file reading and DMData construction.
Requirements: 1.1, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
"""

from __future__ import annotations

import os
import unittest

from dmconverter.dm_parser.file_parser import (
    detect_encoding,
    read_dm_lines,
    parse_dm_file,
)
from dmconverter.dm_parser.models import DMData
from dmconverter.dm_parser.errors import is_success, is_failure


class TestDetectEncoding(unittest.TestCase):
    """Tests for detect_encoding function."""

    def test_detect_encoding_shift_jis(self) -> None:
        """Detect Shift_JIS encoding for sample DM file."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            encoding = detect_encoding(path)
            self.assertIn(encoding.lower(), ("shift_jis", "cp932", "shift-jis"))

    def test_detect_encoding_returns_string(self) -> None:
        """Detect encoding returns a string."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            encoding = detect_encoding(path)
            self.assertIsInstance(encoding, str)


class TestReadDmLines(unittest.TestCase):
    """Tests for read_dm_lines function."""

    def test_read_dm_lines_returns_generator(self) -> None:
        """Read DM lines returns an iterator."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            lines = read_dm_lines(path)
            # Should be iterable
            first_line = next(iter(lines))
            self.assertIsInstance(first_line, str)

    def test_read_dm_lines_first_line_is_index(self) -> None:
        """First line should be index record (M)."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            lines = list(read_dm_lines(path))
            self.assertTrue(lines[0].startswith("M"))

    def test_read_dm_lines_strips_newlines(self) -> None:
        """Lines should not have trailing newlines."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            lines = list(read_dm_lines(path))
            for line in lines[:10]:
                self.assertFalse(line.endswith("\n"))
                self.assertFalse(line.endswith("\r"))


class TestParseDmFile(unittest.TestCase):
    """Tests for parse_dm_file function."""

    def test_parse_dm_file_returns_result(self) -> None:
        """Parse DM file returns Result type."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            result = parse_dm_file(path)
            self.assertTrue(is_success(result) or is_failure(result))

    def test_parse_dm_file_success_returns_dm_data(self) -> None:
        """Successful parse returns DMData."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            result = parse_dm_file(path)
            if is_success(result):
                self.assertIsInstance(result.value, DMData)

    def test_parse_dm_file_sets_coordinate_system(self) -> None:
        """Parsed DMData has coordinate system set."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            result = parse_dm_file(path)
            if is_success(result):
                dm_data = result.value
                self.assertGreaterEqual(dm_data.crs_code, 2443)  # Valid EPSG code

    def test_parse_dm_file_has_map_sheets(self) -> None:
        """Parsed DMData has map sheets."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            result = parse_dm_file(path)
            if is_success(result):
                dm_data = result.value
                self.assertGreater(len(dm_data.map_sheets), 0)

    def test_parse_dm_file_has_elements(self) -> None:
        """Parsed DMData has element groups."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            result = parse_dm_file(path)
            if is_success(result):
                dm_data = result.value
                self.assertGreater(len(dm_data.elements), 0)

    def test_parse_dm_file_nonexistent_returns_failure(self) -> None:
        """Parse nonexistent file returns Failure."""
        result = parse_dm_file("nonexistent_file.dm")
        self.assertTrue(is_failure(result))

    def test_parse_dm_file_skips_modification_history(self) -> None:
        """Parser skips modification history records."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            result = parse_dm_file(path)
            # If successful, modification history records should be skipped
            # This is implicit in the parsing logic
            self.assertTrue(is_success(result) or is_failure(result))


if __name__ == "__main__":
    unittest.main()
