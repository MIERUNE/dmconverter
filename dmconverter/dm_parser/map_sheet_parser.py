"""Map sheet record parsing functions for DM files.

This module provides functions to parse map sheet records from DM files.
Map sheet records contain information about the survey metadata, coordinate
bounds, and reference coordinates for converting relative to absolute coordinates.

Functions:
    - parse_map_sheet_record_a: Parse the survey info line
    - parse_map_sheet_record_b: Parse the organization line
    - parse_map_sheet_records: Combine all lines into a MapSheetRecord
"""

from __future__ import annotations

from dmconverter.dm_parser.index_record_parser import (
    parse_index_record_a,
    parse_index_record_b,
)
from dmconverter.dm_parser.models import Coordinate, MapSheetRecord
from dmconverter.dm_parser.record_helpers import extract_field, parse_int


def parse_map_sheet_record_a(line: str) -> dict[str, str | int]:
    """Parse the survey information line of map sheet records.

    Extracts survey date, software name, project name, and map info level
    from the first map sheet record line.

    Args:
        line: The survey info line (typically starts with date digits)

    Returns:
        Dictionary containing:
            - survey_date: Survey date string
            - software_name: Name of the surveying software
            - project_name: Name of the survey project
            - map_info_level: Map information level (500, 1000, 2500, etc.)
    """
    # Parse the line - format varies but typically:
    # [0-9]: Date/code info
    # [10-29]: Software name (full-width chars)
    # [30-49]: Project name (full-width chars)
    # [50+]: Map info level and flags

    # Extract survey date (first digits)
    survey_date = extract_field(line, 0, 10)

    # Software name - variable position due to full-width chars
    # Find where numbers end and text begins
    software_name = ""
    project_name = ""

    # Try to find map info level (usually "1000" or similar)
    # It's typically near the end of the line
    parts = line.split()
    map_info_level = 1000  # Default

    for part in parts:
        stripped = part.strip()
        if stripped.isdigit() and len(stripped) == 4:
            level = parse_int(stripped, 0)
            if level in (500, 1000, 2500, 5000, 10000, 25000):
                map_info_level = level
                break

    # Extract software and project names from middle section
    # This is complex due to full-width characters
    if len(line) > 10:
        # Try to find the section between date and map level
        middle = line[10:]
        # Split by spaces and filter
        text_parts = [p for p in middle.split() if not p.isdigit()]
        if text_parts:
            software_name = text_parts[0] if len(text_parts) > 0 else ""
            project_name = text_parts[1] if len(text_parts) > 1 else ""

    return {
        "survey_date": survey_date,
        "software_name": software_name,
        "project_name": project_name,
        "map_info_level": map_info_level,
    }


def parse_map_sheet_record_b(line: str) -> dict[str, str]:
    """Parse the organization line of map sheet records.

    Extracts organization name from the second map sheet record line.

    Args:
        line: The organization line (contains organization name)

    Returns:
        Dictionary containing:
            - organization_name: Name of the surveying organization
    """
    # Organization name is typically at the beginning of the line
    # followed by padding and numeric flags

    # Find where the text ends (before numeric data)
    org_end = len(line)
    for i, ch in enumerate(line):
        if ch.isdigit() and i > 10:
            # Check if this is the start of numeric section
            remaining = line[i:].strip()
            if remaining and all(c.isdigit() or c.isspace() for c in remaining):
                org_end = i
                break

    organization_name = line[:org_end].strip()

    return {
        "organization_name": organization_name,
    }


def parse_map_sheet_records(
    index_lines: tuple[str, ...],
    sheet_lines: tuple[str, ...],
) -> MapSheetRecord:
    """Parse map sheet records into a MapSheetRecord.

    Combines data from index records and map sheet records to create
    a complete MapSheetRecord with bounds, base coordinates, and metadata.

    Args:
        index_lines: Tuple of index record lines (a, b, c)
        sheet_lines: Tuple of map sheet record lines

    Returns:
        MapSheetRecord containing all parsed metadata
    """
    # Parse index records for coordinate info
    index_a = parse_index_record_a(index_lines[0]) if len(index_lines) > 0 else {}
    index_b = parse_index_record_b(index_lines[1]) if len(index_lines) > 1 else {}

    # Parse sheet records for survey metadata
    sheet_a = parse_map_sheet_record_a(sheet_lines[0]) if len(sheet_lines) > 0 else {}
    sheet_b = parse_map_sheet_record_b(sheet_lines[1]) if len(sheet_lines) > 1 else {}

    # Extract values
    sheet_id = str(index_a.get("map_sheet_id", ""))
    sheet_name = str(index_a.get("sheet_name", ""))
    map_info_level = int(index_a.get("map_info_level", 1000))

    # Build title from project name or organization
    title = str(sheet_a.get("project_name", ""))
    if not title:
        title = str(sheet_b.get("organization_name", ""))

    # Get bounds from index record (b)
    bounds_tuple = index_b.get("bounds", (0, 0, 0, 0))
    if isinstance(bounds_tuple, tuple) and len(bounds_tuple) == 4:
        bounds = (
            float(bounds_tuple[0]),
            float(bounds_tuple[1]),
            float(bounds_tuple[2]),
            float(bounds_tuple[3]),
        )
    else:
        bounds = (0.0, 0.0, 0.0, 0.0)

    # Get base coordinate from index record (b)
    base_x = float(index_b.get("base_x", 0))
    base_y = float(index_b.get("base_y", 0))
    base_coordinate = Coordinate(x=base_x, y=base_y, z=None)

    # Get coordinate unit
    coordinate_unit = int(index_b.get("coordinate_unit", 1))

    # Survey result code (geodetic datum) - default to JGD2011 (code 2)
    # This may need to be extracted from other records
    survey_result_code = 2

    return MapSheetRecord(
        sheet_id=sheet_id,
        sheet_name=sheet_name,
        map_info_level=map_info_level,
        title=title,
        bounds=bounds,
        base_coordinate=base_coordinate,
        coordinate_unit=coordinate_unit,
        survey_result_code=survey_result_code,
    )
