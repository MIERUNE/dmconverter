"""Index record parsing functions for DM files.

This module provides functions to parse index records (the first few lines)
of a DM file. Index records contain metadata about the file including
coordinate system, organization, and map sheet information.

Index record format:
    Line (a): Record type, map sheet ID, sheet name, map info level, organization, coordinate system
    Line (b): Coordinate bounds, base coordinates, coordinate unit
    Line (c): Adjacent map sheet IDs

Functions:
    - parse_index_record_a: Parse the first line of index records
    - parse_index_record_b: Parse the coordinate bounds line
    - parse_index_record_c: Parse the adjacent sheet IDs line
    - parse_index_records: Combine all index lines into an IndexRecord
"""

from __future__ import annotations

from dmconverter.dm_parser.models import IndexRecord
from dmconverter.dm_parser.record_helpers import extract_field, parse_int


def parse_index_record_a(line: str) -> dict[str, str | int]:
    """Parse the first line of index records.

    Extracts record type, map sheet ID, sheet name, map info level,
    organization name, and coordinate system code from the first index line.

    Args:
        line: The first line of the index record (typically starts with 'M')

    Returns:
        Dictionary containing:
            - record_type: Record type character ('M')
            - map_sheet_id: Map sheet identifier
            - sheet_name: Human-readable sheet name
            - map_info_level: Map information level (e.g., 500, 1000, 2500)
            - organization_name: Name of the organization
            - coordinate_system: Plane rectangular coordinate system code (1-19)
    """
    # Position 0: Record type ('M' for map)
    record_type = extract_field(line, 0, 1)

    # Position 2-8: Map sheet ID (7 characters)
    map_sheet_id = extract_field(line, 2, 9)

    # Position 10-28: Sheet name (up to 19 characters in decoded string)
    # Note: Full-width characters take 2 bytes in Shift_JIS
    sheet_name = extract_field(line, 10, 29)

    # Position 29-32: Map info level (4 digits)
    map_info_level_str = extract_field(line, 29, 33)
    map_info_level = parse_int(map_info_level_str, 1000)

    # Position 33-52: Organization name
    organization_name = extract_field(line, 33, 53)

    # Extract coordinate system code from map sheet ID
    # Japanese DM map sheet IDs start with 2-digit coordinate system code
    # e.g., "02JF613" -> coordinate system 2
    coordinate_system = 1  # Default
    if map_sheet_id and len(map_sheet_id) >= 2:
        coord_sys_str = map_sheet_id[:2]
        coord_sys = parse_int(coord_sys_str, 0)
        if 1 <= coord_sys <= 19:
            coordinate_system = coord_sys

    return {
        "record_type": record_type,
        "map_sheet_id": map_sheet_id,
        "sheet_name": sheet_name,
        "map_info_level": map_info_level,
        "organization_name": organization_name,
        "coordinate_system": coordinate_system,
    }


def parse_index_record_b(line: str) -> dict[str, tuple[int, int, int, int] | int]:
    """Parse the coordinate bounds line of index records.

    Extracts coordinate bounds, base coordinates, and coordinate unit
    from the second index line.

    Args:
        line: The second line of the index record (coordinate bounds)

    Returns:
        Dictionary containing:
            - bounds: Tuple of (min_x, min_y, max_x, max_y)
            - base_x: Base X coordinate for relative-to-absolute conversion
            - base_y: Base Y coordinate for relative-to-absolute conversion
            - coordinate_unit: Unit code (1=m, 10=cm, 999=mm)
    """
    # Split by whitespace and parse numeric values
    parts = line.split()

    # Default values
    bounds = (0, 0, 0, 0)
    base_x = 0
    base_y = 0
    coordinate_unit = 1

    if len(parts) >= 4:
        # First 4 values: bounds (min_x, min_y, max_x, max_y)
        bounds = (
            parse_int(parts[0]),
            parse_int(parts[1]),
            parse_int(parts[2]),
            parse_int(parts[3]),
        )

    if len(parts) >= 6:
        # Next 2 values: base coordinates
        base_x = parse_int(parts[4])
        base_y = parse_int(parts[5])

    if len(parts) >= 7:
        # Next value: coordinate unit
        coordinate_unit = parse_int(parts[6], 1)

    return {
        "bounds": bounds,
        "base_x": base_x,
        "base_y": base_y,
        "coordinate_unit": coordinate_unit,
    }


def parse_index_record_c(line: str) -> dict[str, tuple[str, ...]]:
    """Parse the adjacent map sheet IDs line of index records.

    Extracts adjacent map sheet identifiers from the third index line.

    Args:
        line: The third line of the index record (adjacent sheet IDs)

    Returns:
        Dictionary containing:
            - adjacent_sheets: Tuple of adjacent map sheet ID strings
    """
    # Split by whitespace to get individual sheet IDs
    parts = line.split()

    # Filter out empty strings and return as tuple
    adjacent_sheets = tuple(p for p in parts if p.strip())

    return {
        "adjacent_sheets": adjacent_sheets,
    }


def parse_index_records(lines: tuple[str, ...]) -> IndexRecord:
    """Parse multiple index record lines into an IndexRecord.

    Combines data from index record lines (a), (b), and (c) into
    a single IndexRecord dataclass.

    Args:
        lines: Tuple of index record lines (typically 3 lines)

    Returns:
        IndexRecord containing all parsed metadata

    Note:
        The record_type is always set to "A" for IndexRecord as per
        the data model specification, regardless of the actual character
        in the file (which is typically 'M').
    """
    # Parse each line
    record_a = parse_index_record_a(lines[0]) if len(lines) > 0 else {}
    # record_b and record_c are not directly used in IndexRecord
    # but may be used for MapSheetRecord

    # Extract values for IndexRecord
    coordinate_system = record_a.get("coordinate_system", 1)
    organization_name = record_a.get("organization_name", "")

    # Ensure coordinate_system is an int
    if isinstance(coordinate_system, str):
        coordinate_system = parse_int(coordinate_system, 1)

    # Ensure organization_name is a string
    if not isinstance(organization_name, str):
        organization_name = str(organization_name)

    # Create IndexRecord with default values for fields not in index records
    # These will be populated from other parts of the file during full parsing
    return IndexRecord(
        record_type="A",  # Always "A" for IndexRecord per specification
        coordinate_system=coordinate_system,
        organization_name=organization_name,
        map_sheet_count=1,  # Default, to be updated during full parsing
        classification_code_count=0,  # Default, to be updated during full parsing
        work_standard_name="",  # Default, to be updated during full parsing
        version=1,  # Default version
    )
