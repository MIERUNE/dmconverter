"""Helper functions for parsing DM record fields.

This module provides utility functions for extracting and parsing
fields from fixed-length 80-byte DM records.

Functions:
    - extract_field: Extract substring from fixed-length record
    - parse_int: Parse string to integer with default value
    - parse_float: Parse string to float with default value
    - is_modification_history_record: Check if record is modification history
    - should_skip_record: Check if record should be skipped during parsing
"""

from __future__ import annotations


def extract_field(line: str, start: int, end: int) -> str:
    """Extract and strip a field from a fixed-length record.

    Extracts characters from position start (inclusive) to end (exclusive)
    and strips leading/trailing whitespace.

    Args:
        line: The record line to extract from
        start: Start position (0-indexed, inclusive)
        end: End position (0-indexed, exclusive)

    Returns:
        Extracted field with whitespace stripped, empty string if positions
        are out of bounds
    """
    if start >= len(line):
        return ""
    actual_end = min(end, len(line))
    return line[start:actual_end].strip()


def parse_int(value: str, default: int = 0) -> int:
    """Parse string to integer with default value on failure.

    Handles empty strings, whitespace-only strings, and invalid formats
    by returning the default value.

    Args:
        value: String to parse
        default: Value to return on parse failure

    Returns:
        Parsed integer or default value
    """
    stripped = value.strip()
    if not stripped:
        return default
    try:
        return int(stripped)
    except ValueError:
        return default


def parse_float(value: str, default: float = 0.0) -> float:
    """Parse string to float with default value on failure.

    Handles empty strings, whitespace-only strings, and invalid formats
    by returning the default value. Supports scientific notation.

    Args:
        value: String to parse
        default: Value to return on parse failure

    Returns:
        Parsed float or default value
    """
    stripped = value.strip()
    if not stripped:
        return default
    try:
        return float(stripped)
    except ValueError:
        return default


# Position of history management code in DM records (0-indexed)
# The last character of the 80-byte record indicates modification history
HISTORY_CODE_POSITION = 79


def is_modification_history_record(line: str) -> bool:
    """Check if record is a modification history record.

    DM files can contain modification history records that should be
    skipped to process only the latest data. The history management
    code is stored at position 79 (last position of 80-byte record).

    History codes:
        - '0' or space: Current/latest data (not history)
        - '1', '2', etc.: Modification history (should skip)

    Args:
        line: The record line to check

    Returns:
        True if record is modification history, False otherwise
    """
    if len(line) < HISTORY_CODE_POSITION + 1:
        return False

    history_code = line[HISTORY_CODE_POSITION]
    # History codes 1, 2, 3, etc. indicate modification history
    # Code 0 or space indicates current data
    return history_code in ("1", "2", "3", "4", "5", "6", "7", "8", "9")


def should_skip_record(line: str) -> bool:
    """Check if record should be skipped during parsing.

    Records should be skipped if they are modification history records
    or other invalid/obsolete records.

    Args:
        line: The record line to check

    Returns:
        True if record should be skipped, False otherwise
    """
    # Skip modification history records
    if is_modification_history_record(line):
        return True

    # Add other skip conditions here if needed
    return False
