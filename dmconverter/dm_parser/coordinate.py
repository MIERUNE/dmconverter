"""Coordinate processing functions for DM files.

This module provides functions for coordinate system identification,
EPSG code conversion, and coordinate value normalization.

Japan uses 19 different Plane Rectangular Coordinate Systems (平面直角座標系),
each with its own EPSG code depending on the geodetic datum (JGD2011 or JGD2000).

Constants:
    - EPSG_JGD2011: Mapping from coordinate system code to EPSG code (JGD2011)
    - EPSG_JGD2000: Mapping from coordinate system code to EPSG code (JGD2000)

Functions:
    - get_geodetic_datum: Get datum name from survey result code
    - get_epsg_code: Get EPSG code for coordinate system and datum
    - normalize_coordinate_unit: Convert coordinate to meters
    - relative_to_absolute: Convert relative to absolute coordinates
    - is_valid_z_coordinate: Check if Z coordinate is valid
"""

from __future__ import annotations

from typing import Literal, Union

from dmconverter.dm_parser.models import Coordinate

# Type alias for geodetic datum
GeodeticDatumType = Literal["JGD2011", "JGD2000"]

# EPSG codes for JGD2011 (Japan Geodetic Datum 2011)
# Coordinate systems 1-19
EPSG_JGD2011: dict[int, int] = {
    1: 6669,
    2: 6670,
    3: 6671,
    4: 6672,
    5: 6673,
    6: 6674,
    7: 6675,
    8: 6676,
    9: 6677,
    10: 6678,
    11: 6679,
    12: 6680,
    13: 6681,
    14: 6682,
    15: 6683,
    16: 6684,
    17: 6685,
    18: 6686,
    19: 6687,
}

# EPSG codes for JGD2000 (Japan Geodetic Datum 2000)
# Coordinate systems 1-19
EPSG_JGD2000: dict[int, int] = {
    1: 2443,
    2: 2444,
    3: 2445,
    4: 2446,
    5: 2447,
    6: 2448,
    7: 2449,
    8: 2450,
    9: 2451,
    10: 2452,
    11: 2453,
    12: 2454,
    13: 2455,
    14: 2456,
    15: 2457,
    16: 2458,
    17: 2459,
    18: 2460,
    19: 2461,
}


def get_geodetic_datum(survey_result_code: int) -> GeodeticDatumType:
    """Get geodetic datum name from survey result code.

    The survey result code indicates which geodetic datum was used
    for the survey measurements.

    Args:
        survey_result_code: Survey result code from DM file
            - 0: JGD2000
            - 1: JGD2000
            - 2: JGD2011
            - Other: Defaults to JGD2011

    Returns:
        Geodetic datum name ("JGD2011" or "JGD2000")
    """
    if survey_result_code in (0, 1):
        return "JGD2000"
    return "JGD2011"


def get_epsg_code(
    coordinate_system: int,
    datum: GeodeticDatumType,
) -> int:
    """Get EPSG code for a coordinate system and datum combination.

    Japan uses 19 different Plane Rectangular Coordinate Systems,
    each covering a different region of the country.

    Args:
        coordinate_system: Coordinate system code (1-19)
        datum: Geodetic datum ("JGD2011" or "JGD2000")

    Returns:
        EPSG code for the coordinate reference system

    Raises:
        ValueError: If coordinate system code is out of range
    """
    if coordinate_system < 1 or coordinate_system > 19:
        raise ValueError(
            f"Coordinate system must be 1-19, got {coordinate_system}"
        )

    if datum == "JGD2011":
        return EPSG_JGD2011[coordinate_system]
    else:
        return EPSG_JGD2000[coordinate_system]


def normalize_coordinate_unit(value: float, unit_code: int) -> float:
    """Normalize coordinate value to meters.

    DM files can store coordinates in meters, centimeters, or millimeters.
    This function converts the value to meters for consistent processing.

    Args:
        value: Coordinate value in original units
        unit_code: Unit code
            - 1: Meters
            - 10: Centimeters
            - 999: Millimeters

    Returns:
        Coordinate value in meters
    """
    if unit_code == 10:
        # Centimeters to meters
        return value / 100.0
    elif unit_code == 999:
        # Millimeters to meters
        return value / 1000.0
    else:
        # Assume meters (unit_code == 1)
        return float(value)


def relative_to_absolute(
    relative: Coordinate,
    base: Coordinate,
) -> Coordinate:
    """Convert relative coordinate to absolute coordinate.

    DM files store coordinates relative to a base point (typically the
    lower-left corner of the map sheet). This function adds the base
    coordinate to convert to absolute values.

    Args:
        relative: Relative coordinate (offset from base)
        base: Base coordinate (lower-left corner)

    Returns:
        Absolute coordinate
    """
    new_x = relative.x + base.x
    new_y = relative.y + base.y

    # Z coordinate is typically absolute, not relative
    new_z = relative.z

    return Coordinate(x=new_x, y=new_y, z=new_z)


def is_valid_z_coordinate(z: Union[float, None]) -> bool:
    """Check if a Z coordinate value is valid.

    DM files use special values like -999 or -9999 to indicate
    that no Z coordinate data is available.

    Args:
        z: Z coordinate value or None

    Returns:
        True if the Z coordinate is a valid elevation value
    """
    if z is None:
        return False

    # Common "no data" values in DM files
    invalid_values = (-999.0, -9999.0, -99999.0)

    return z not in invalid_values
