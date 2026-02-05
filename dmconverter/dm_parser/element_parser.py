"""Element record parsing functions for DM files.

This module provides functions to parse element records, header records,
coordinate lines, annotation records, and attribute records from DM files.

Element types:
    - E1: Polygon (closed area)
    - E2: Line (polyline)
    - E3: Circle
    - E4: Arc
    - E5: Point
    - E6: Direction (point with direction)
    - E7: Annotation (text)
    - E8: Attribute (user-defined)

Functions:
    - parse_header_record: Parse layer/group header records
    - parse_element_record: Parse element (E) records
    - parse_coordinate_line: Parse coordinate data lines
    - parse_annotation_record: Parse annotation text records
    - parse_attribute_record: Parse attribute key-value records
"""

from __future__ import annotations

from typing import Literal

from dmconverter.dm_parser.record_helpers import extract_field, parse_int, parse_float


# Data type mapping
DATA_TYPE_MAP: dict[int, Literal["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"]] = {
    1: "E1",  # Polygon
    2: "E2",  # Line
    3: "E3",  # Circle
    4: "E4",  # Arc
    5: "E5",  # Point
    6: "E6",  # Direction
    7: "E7",  # Annotation
    8: "E8",  # Attribute
}


def parse_header_record(line: str) -> dict[str, str | int]:
    """Parse a header (H) record.

    Header records define layers and element groups within the DM file.
    They contain classification codes and element counts.

    Args:
        line: The header record line (starts with 'H')

    Returns:
        Dictionary containing:
            - record_type: 'H'
            - classification_code: Classification code string
            - element_count: Number of elements in this group
            - hierarchy_level: Hierarchy level
    """
    record_type = extract_field(line, 0, 1)

    # Classification code at positions 2-5 (4 digits)
    classification_code = extract_field(line, 2, 6)

    # Various counts and flags follow
    # Position 7-10: flags
    # Position 11-14: flags
    # Position 15: hierarchy level
    hierarchy_level = parse_int(extract_field(line, 15, 16), 1)

    # Element counts - position varies
    # Try to find element count around positions 17-21
    count_str = extract_field(line, 17, 22)
    element_count = parse_int(count_str, 0)

    return {
        "record_type": record_type,
        "classification_code": classification_code,
        "element_count": element_count,
        "hierarchy_level": hierarchy_level,
    }


def parse_element_record(line: str) -> dict[str, str | int]:
    """Parse an element (E) record.

    Element records define geographic features with classification codes,
    data types, and coordinate counts.

    DM Record Format (positions are 0-indexed):
        - Position 0-1: Data type (E1, E2, E3, E4, E5, E6, E7, E8)
        - Position 2-5: Classification code (4 digits)
        - Position 6-14: Flags
        - Position 15: Hierarchy level
        - Position 27-30: Coordinate count
        - Position 31-34: Line count

    Args:
        line: The element record line (starts with 'E')

    Returns:
        Dictionary containing:
            - record_type: 'E'
            - classification_code: 4-digit classification code
            - data_type: Element type (E1-E8)
            - hierarchy_level: Hierarchy level within classification
            - coordinate_count: Number of coordinate points
            - line_count: Number of coordinate lines following
    """
    record_type = extract_field(line, 0, 1)

    # Data type is at positions 0-1 (E1, E2, E5, E6, E7, etc.)
    data_type_str = extract_field(line, 0, 2)
    if data_type_str in ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"):
        data_type: Literal["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"] = data_type_str  # type: ignore
    else:
        data_type = "E2"  # Default to line

    # Classification code at positions 2-5 (4 digits)
    classification_code = extract_field(line, 2, 6)

    # Position 15: hierarchy level
    hierarchy_level = parse_int(extract_field(line, 15, 16), 1)

    # Position 27-30: coordinate count (with leading spaces)
    coordinate_count = parse_int(extract_field(line, 27, 31), 0)

    # Position 31-34: line count
    line_count = parse_int(extract_field(line, 31, 35), 0)

    return {
        "record_type": record_type,
        "classification_code": classification_code,
        "data_type": data_type,
        "hierarchy_level": hierarchy_level,
        "coordinate_count": coordinate_count,
        "line_count": line_count,
    }


def parse_coordinate_line(
    line: str,
    is_3d: bool = False,
) -> list[tuple[int, int] | tuple[int, int, int]]:
    """Parse a coordinate data line.

    Coordinate lines contain pairs (2D) or triples (3D) of coordinate values
    packed consecutively.

    Args:
        line: The coordinate data line
        is_3d: Whether coordinates are 3D (x, y, z) or 2D (x, y)

    Returns:
        List of coordinate tuples
    """
    # Split by whitespace and parse as integers
    parts = line.split()
    coords: list[tuple[int, int] | tuple[int, int, int]] = []

    if is_3d:
        # 3D coordinates: every 3 values form (x, y, z)
        for i in range(0, len(parts) - 2, 3):
            x = parse_int(parts[i], 0)
            y = parse_int(parts[i + 1], 0)
            z = parse_int(parts[i + 2], 0)
            coords.append((x, y, z))
    else:
        # 2D coordinates: every 2 values form (x, y)
        for i in range(0, len(parts) - 1, 2):
            x = parse_int(parts[i], 0)
            y = parse_int(parts[i + 1], 0)
            coords.append((x, y))

    return coords


def parse_annotation_record(line: str) -> dict[str, str | float]:
    """Parse an annotation record.

    Annotation records contain text display properties including
    orientation, direction angle, font size, and the text content.

    Args:
        line: The annotation record line

    Returns:
        Dictionary containing:
            - orientation: 'horizontal' or 'vertical'
            - direction: Text rotation angle in degrees
            - font_size: Font size in 0.1mm units
            - char_spacing: Character spacing in 0.1mm units
            - text: The annotation text content
    """
    # Position 0: orientation code (1=horizontal, 2=vertical)
    orientation_code = parse_int(extract_field(line, 0, 1), 1)
    orientation: Literal["horizontal", "vertical"] = (
        "horizontal" if orientation_code == 1 else "vertical"
    )

    # Position 2-4: direction angle (degrees * 10 or similar)
    direction_str = extract_field(line, 2, 5)
    direction = parse_float(direction_str, 0.0)

    # Position 6-8: font size
    font_size_str = extract_field(line, 6, 8)
    font_size = parse_float(font_size_str, 0.0)

    # Position 9-11: character spacing
    char_spacing_str = extract_field(line, 9, 11)
    char_spacing = parse_float(char_spacing_str, 0.0)

    # Position 12+: text content
    text = extract_field(line, 12, len(line))

    return {
        "orientation": orientation,
        "direction": direction,
        "font_size": font_size,
        "char_spacing": char_spacing,
        "text": text,
    }


def parse_attribute_record(line: str) -> dict[str, list[tuple[str, str]]]:
    """Parse an attribute record.

    Attribute records contain user-defined key-value pairs.
    Format is typically "KEY=VALUE" or similar.

    Args:
        line: The attribute record line

    Returns:
        Dictionary containing:
            - attributes: List of (key, value) tuples
    """
    attributes: list[tuple[str, str]] = []

    # Try to parse key=value format
    stripped = line.strip()
    if "=" in stripped:
        # Split on first = only
        eq_pos = stripped.index("=")
        key = stripped[:eq_pos].strip()
        value = stripped[eq_pos + 1 :].strip()
        attributes.append((key, value))
    elif stripped:
        # If no = found, treat whole line as a value with empty key
        attributes.append(("", stripped))

    return {
        "attributes": attributes,
    }
