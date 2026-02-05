"""File parsing functions for DM files.

This module provides functions to read and parse DM (Digital Map) files,
detecting encoding and constructing the DMData structure from the records.

Functions:
    - detect_encoding: Detect file encoding (Shift_JIS or UTF-8)
    - read_dm_lines: Read DM file lines as iterator
    - parse_dm_file: Parse entire DM file into DMData structure
"""

from __future__ import annotations

import os
from typing import Iterator, Union

from dmconverter.dm_parser.coordinate import get_epsg_code, get_geodetic_datum
from dmconverter.dm_parser.element_parser import (
    parse_coordinate_line,
    parse_element_record,
    parse_header_record,
)
from dmconverter.dm_parser.errors import (
    ERROR_FILE_NOT_FOUND,
    ERROR_INVALID_DM_FILE,
    ERROR_RECORD_PARSE,
    Failure,
    Result,
    Success,
)
from dmconverter.dm_parser.index_record_parser import (
    parse_index_record_a,
    parse_index_record_b,
    parse_index_records,
)
from dmconverter.dm_parser.map_sheet_parser import parse_map_sheet_records
from dmconverter.dm_parser.models import (
    Coordinate,
    DMData,
    ElementGroup,
    ElementRecord,
    IndexRecord,
    MapSheetRecord,
)
from dmconverter.dm_parser.record_helpers import should_skip_record, parse_int


def parse_fixed_width_coordinates(line: str, max_coords: int = 100) -> list[tuple[int, int]]:
    """Parse coordinates in 7-char fixed-width format.

    DM coordinate lines use 7-character fields for each value.
    Coordinates are stored as X, Y pairs where each value is 7 characters.

    Args:
        line: The coordinate line
        max_coords: Maximum number of coordinate pairs to parse (safety limit)

    Returns:
        List of (x, y) tuples with raw values (in 0.1mm units)
    """
    coords: list[tuple[int, int]] = []

    for i in range(max_coords):
        # Each coordinate pair is 14 characters (7 for X, 7 for Y)
        start = i * 14
        if start + 14 > len(line):
            break

        x_str = line[start : start + 7]
        y_str = line[start + 7 : start + 14]

        # Check for zero padding or spaces (end of valid data)
        x_stripped = x_str.strip()
        y_stripped = y_str.strip()

        if not x_stripped or x_stripped == "0":
            break
        if not y_stripped or y_stripped == "0":
            break

        x = parse_int(x_str, 0)
        y = parse_int(y_str, 0)

        # Skip if both are zero (padding)
        if x == 0 and y == 0:
            break

        coords.append((x, y))

    return coords


def parse_embedded_coordinate(line: str) -> tuple[int, int] | None:
    """Parse coordinate embedded in E record at position 35-48.

    Used for E5 (point), E6 (direction), E7 (annotation) where
    coordinates are embedded in the E record itself.

    Args:
        line: The E record line

    Returns:
        (x, y) tuple or None if parsing fails
    """
    if len(line) >= 49:
        x_str = line[35:42]
        y_str = line[42:49]
        x = parse_int(x_str, 0)
        y = parse_int(y_str, 0)
        if x != 0 or y != 0:
            return (x, y)
    return None


def detect_encoding(file_path: str) -> str:
    """Detect the encoding of a DM file.

    DM files are typically encoded in Shift_JIS (CP932) but may
    occasionally be in UTF-8.

    Args:
        file_path: Path to the DM file

    Returns:
        Detected encoding name (e.g., "shift_jis", "utf-8")
    """
    # Read first few bytes to detect encoding
    try:
        with open(file_path, "rb") as f:
            raw = f.read(1000)

        # Try UTF-8 first (if BOM present or valid UTF-8)
        if raw.startswith(b"\xef\xbb\xbf"):
            return "utf-8"

        try:
            raw.decode("utf-8")
            # Check if it has Japanese characters that would indicate Shift_JIS
            # If pure ASCII, prefer Shift_JIS for DM files
            if all(b < 128 for b in raw):
                return "shift_jis"
            return "utf-8"
        except UnicodeDecodeError:
            pass

        # Try Shift_JIS
        try:
            raw.decode("shift_jis")
            return "shift_jis"
        except UnicodeDecodeError:
            pass

        # Default to Shift_JIS for DM files
        return "shift_jis"

    except IOError:
        return "shift_jis"


def read_dm_lines(file_path: str, encoding: str | None = None) -> Iterator[str]:
    """Read DM file lines as an iterator.

    Handles encoding detection and line splitting for DM files,
    which typically use CRLF line endings.

    Args:
        file_path: Path to the DM file
        encoding: Encoding to use (auto-detected if None)

    Yields:
        Individual lines from the file with newlines stripped
    """
    if encoding is None:
        encoding = detect_encoding(file_path)

    with open(file_path, "rb") as f:
        raw = f.read()

    # Decode and split by CRLF or LF
    try:
        content = raw.decode(encoding)
    except UnicodeDecodeError:
        # Fallback to shift_jis with error handling
        content = raw.decode("shift_jis", errors="replace")

    # Split by CRLF first, then by LF for any remaining
    lines = content.replace("\r\n", "\n").split("\n")

    for line in lines:
        if line:  # Skip empty lines
            yield line


def parse_dm_file(file_path: str) -> Result[DMData]:
    """Parse a DM file into a DMData structure.

    Reads the entire file, parses all records, and constructs
    the DMData structure with index, map sheets, and elements.

    Args:
        file_path: Path to the DM file

    Returns:
        Result containing DMData on success, or Failure on error
    """
    # Check file exists
    if not os.path.exists(file_path):
        return Failure(
            error_type=ERROR_FILE_NOT_FOUND,
            message=f"File not found: {file_path}",
            context={"file": file_path},
        )

    try:
        # Read all lines
        lines = list(read_dm_lines(file_path))

        if len(lines) < 3:
            return Failure(
                error_type=ERROR_INVALID_DM_FILE,
                message="File too short to be a valid DM file",
                context={"file": file_path, "lines": str(len(lines))},
            )

        # Parse index records (first 3 lines)
        index_lines = tuple(lines[:3])
        index_record = parse_index_records(index_lines)

        # Parse index record (b) for coordinate info
        index_b = parse_index_record_b(lines[1])

        # Find map sheet records (lines after index, before H records)
        sheet_lines: list[str] = []
        current_line = 3

        while current_line < len(lines):
            line = lines[current_line]
            if line.startswith("H") or line.startswith("E"):
                break
            if not should_skip_record(line):
                sheet_lines.append(line)
            current_line += 1

        # Parse map sheet
        map_sheet = parse_map_sheet_records(
            index_lines,
            tuple(sheet_lines) if sheet_lines else ("", ""),
        )

        # Get coordinate system and datum
        coordinate_system = index_record.coordinate_system
        survey_result_code = map_sheet.survey_result_code
        datum = get_geodetic_datum(survey_result_code)
        crs_code = get_epsg_code(coordinate_system, datum)

        # Parse element groups
        element_groups: list[ElementGroup] = []
        current_group_code = ""
        current_group_level = 0
        current_elements: list[ElementRecord] = []

        # Get map sheet origin for relative-to-absolute conversion
        # Bounds are (min_x, min_y, max_x, max_y) in meters
        bounds = index_b.get("bounds", (0, 0, 0, 0))
        origin_x = float(bounds[0])  # Map sheet X origin (meters)
        origin_y = float(bounds[1])  # Map sheet Y origin (meters)
        # Raw coordinates are in 0.1mm units, divide by 1000 to get meters
        coord_scale = 1000.0

        i = current_line
        while i < len(lines):
            line = lines[i]

            # Skip modification history records
            if should_skip_record(line):
                i += 1
                continue

            # Header record
            if line.startswith("H"):
                # Save previous group if any
                if current_elements:
                    element_groups.append(
                        ElementGroup(
                            classification_code=current_group_code,
                            hierarchy_level=current_group_level,
                            elements=tuple(current_elements),
                        )
                    )
                    current_elements = []

                header = parse_header_record(line)
                current_group_code = str(header.get("classification_code", ""))
                current_group_level = int(header.get("hierarchy_level", 1))
                i += 1

            # Element record
            elif line.startswith("E"):
                element_data = parse_element_record(line)
                classification_code = str(element_data.get("classification_code", ""))
                data_type = str(element_data.get("data_type", "E2"))
                hierarchy_level = int(element_data.get("hierarchy_level", 1))
                line_count = int(element_data.get("line_count", 0))
                coordinate_count = int(element_data.get("coordinate_count", 0))

                # Parse coordinates based on data type
                coords: list[Coordinate] = []

                if data_type in ("E5", "E6", "E7"):
                    # Point, Direction, Annotation: coordinates embedded in E record
                    embedded = parse_embedded_coordinate(line)
                    if embedded:
                        raw_x, raw_y = embedded
                        # Convert from 0.1mm to meters and add origin
                        # Note: DM uses X=North, Y=East but GIS convention is X=East, Y=North
                        # So we swap: GIS_X = DM_Y, GIS_Y = DM_X
                        abs_x = origin_y + (float(raw_y) / coord_scale)  # GIS X = DM Y
                        abs_y = origin_x + (float(raw_x) / coord_scale)  # GIS Y = DM X
                        coords.append(Coordinate(x=abs_x, y=abs_y, z=None))

                else:
                    # E1, E2, E3, E4: all use 7-char fixed-width format
                    for j in range(line_count):
                        coord_line_idx = i + 1 + j
                        if coord_line_idx < len(lines):
                            coord_line = lines[coord_line_idx]
                            if not coord_line.startswith(("H", "E")):
                                # Parse as 7-char fixed-width coordinate pairs
                                raw_coords = parse_fixed_width_coordinates(coord_line)
                                for raw_x, raw_y in raw_coords:
                                    # Convert from 0.1mm to meters and add origin
                                    # Note: DM uses X=North, Y=East but GIS convention is X=East, Y=North
                                    # So we swap: GIS_X = DM_Y, GIS_Y = DM_X
                                    abs_x = origin_y + (float(raw_y) / coord_scale)  # GIS X = DM Y
                                    abs_y = origin_x + (float(raw_x) / coord_scale)  # GIS Y = DM X
                                    coords.append(Coordinate(x=abs_x, y=abs_y, z=None))

                # Create element record
                element = ElementRecord(
                    classification_code=classification_code,
                    data_type=data_type,  # type: ignore
                    hierarchy_level=hierarchy_level,
                    coordinates=tuple(coords),
                    annotation=None,
                    attributes=None,
                )
                current_elements.append(element)

                # Skip coordinate lines
                i += 1 + line_count

            else:
                # Skip other lines (coordinate continuations, etc.)
                i += 1

        # Save last group
        if current_elements:
            element_groups.append(
                ElementGroup(
                    classification_code=current_group_code,
                    hierarchy_level=current_group_level,
                    elements=tuple(current_elements),
                )
            )

        # Create DMData
        dm_data = DMData(
            index=index_record,
            map_sheets=(map_sheet,),
            elements=tuple(element_groups),
            crs_code=crs_code,
            datum=datum,
        )

        return Success(value=dm_data)

    except Exception as e:
        return Failure(
            error_type=ERROR_RECORD_PARSE,
            message=f"Error parsing DM file: {str(e)}",
            context={"file": file_path, "error": str(e)},
        )
