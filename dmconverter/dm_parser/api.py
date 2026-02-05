"""Public API functions for DM Parser.

This module provides the main entry points for parsing DM files
and converting them to QGIS vector layers.

Main Functions:
    - parse_dm_file: Parse a DM file into DMData structure
    - dm_to_layers: Convert DMData to list of QGIS vector layers
    - load_dm_to_qgis: Parse and load DM file directly to QGIS
    - save_dm_to_geopackage: Parse and save DM file to GeoPackage

Example Usage:
    >>> from dmconverter.dm_parser import parse_dm_file, dm_to_layers
    >>> result = parse_dm_file("path/to/file.dm")
    >>> if is_success(result):
    ...     layers = dm_to_layers(result.value)
    ...     for layer in layers:
    ...         QgsProject.instance().addMapLayer(layer)
"""

from __future__ import annotations

from typing import Sequence

from dmconverter.dm_parser.errors import (
    ERROR_FILE_NOT_FOUND,
    ERROR_RECORD_PARSE,
    Failure,
    Result,
    Success,
    is_success,
)
from dmconverter.dm_parser.file_parser import parse_dm_file as _parse_dm_file
from dmconverter.dm_parser.layer_generator import (
    dm_data_to_layers,
    save_layers_to_geopackage,
)
from dmconverter.dm_parser.models import DMData

# Try to import QGIS modules
try:
    from qgis.core import QgsProject, QgsVectorLayer

    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False


def parse_dm_file(file_path: str) -> Result[DMData]:
    """Parse a DM file into a DMData structure.

    This is the main entry point for parsing DM (Digital Map) files.
    The function handles encoding detection, record parsing, and
    coordinate conversion automatically.

    Args:
        file_path: Path to the DM file

    Returns:
        Result containing DMData on success, or Failure with error details

    Example:
        >>> result = parse_dm_file("02JF711.dm")
        >>> if is_success(result):
        ...     dm_data = result.value
        ...     print(f"Parsed {len(dm_data.elements)} element groups")
    """
    return _parse_dm_file(file_path)


def dm_to_layers(
    dm_data: DMData,
    group_by_classification: bool = False,
) -> list["QgsVectorLayer"]:
    """Convert DMData to a list of QGIS vector layers.

    Creates separate layers for different geometry types (point, line, polygon).
    Each layer includes standard attributes for classification code,
    classification name, hierarchy level, and data type.

    Args:
        dm_data: Parsed DM data from parse_dm_file
        group_by_classification: If True, create separate layers for each
                                classification code (not yet implemented)

    Returns:
        List of QgsVectorLayer objects ready to add to QGIS

    Raises:
        ImportError: If QGIS modules are not available

    Example:
        >>> layers = dm_to_layers(dm_data)
        >>> for layer in layers:
        ...     QgsProject.instance().addMapLayer(layer)
    """
    if not QGIS_AVAILABLE:
        raise ImportError("QGIS modules are not available")

    return dm_data_to_layers(dm_data, group_by_classification)


def load_dm_to_qgis(
    file_path: str,
    add_to_project: bool = True,
    group_name: str | None = None,
) -> Result[list["QgsVectorLayer"]]:
    """Parse a DM file and load it directly into QGIS.

    This is a convenience function that combines parsing and layer
    creation in a single call. Optionally adds the layers to the
    current QGIS project.

    Args:
        file_path: Path to the DM file
        add_to_project: If True, add layers to current QGIS project
        group_name: Optional layer group name in the project

    Returns:
        Result containing list of created layers on success,
        or Failure with error details

    Example:
        >>> result = load_dm_to_qgis("02JF711.dm")
        >>> if is_success(result):
        ...     print(f"Loaded {len(result.value)} layers")
    """
    if not QGIS_AVAILABLE:
        return Failure(
            error_type=ERROR_RECORD_PARSE,
            message="QGIS modules are not available",
            context={"file": file_path},
        )

    # Parse the file
    parse_result = parse_dm_file(file_path)
    if not is_success(parse_result):
        return parse_result  # type: ignore

    dm_data = parse_result.value

    # Convert to layers
    try:
        layers = dm_to_layers(dm_data)
    except Exception as e:
        return Failure(
            error_type=ERROR_RECORD_PARSE,
            message=f"Failed to create layers: {str(e)}",
            context={"file": file_path, "error": str(e)},
        )

    # Add to project if requested
    if add_to_project and layers:
        project = QgsProject.instance()

        if group_name:
            # Create layer group
            root = project.layerTreeRoot()
            group = root.addGroup(group_name)
            for layer in layers:
                project.addMapLayer(layer, False)
                group.addLayer(layer)
        else:
            for layer in layers:
                project.addMapLayer(layer)

    return Success(value=layers)


def save_dm_to_geopackage(
    dm_file_path: str,
    output_path: str,
    group_by_classification: bool = False,
) -> Result[str]:
    """Parse a DM file and save it to a GeoPackage file.

    Parses the DM file, creates vector layers, and saves them
    to a single GeoPackage file with multiple layers.

    Args:
        dm_file_path: Path to the input DM file
        output_path: Path for the output GeoPackage file
        group_by_classification: If True, create separate layers for each
                                 2-digit classification code prefix AND geometry type.
                                 Layers will be named like DM_11_Line, DM_30_Point, etc.

    Returns:
        Result containing output path on success,
        or Failure with error details

    Example:
        >>> result = save_dm_to_geopackage("02JF711.dm", "output.gpkg")
        >>> if is_success(result):
        ...     print(f"Saved to {result.value}")

        >>> # With classification grouping
        >>> result = save_dm_to_geopackage("02JF711.dm", "grouped.gpkg", group_by_classification=True)
    """
    if not QGIS_AVAILABLE:
        return Failure(
            error_type=ERROR_RECORD_PARSE,
            message="QGIS modules are not available",
            context={"file": dm_file_path},
        )

    # Parse the file
    parse_result = parse_dm_file(dm_file_path)
    if not is_success(parse_result):
        return Failure(
            error_type=parse_result.error_type,  # type: ignore
            message=parse_result.message,  # type: ignore
            context=parse_result.context,  # type: ignore
        )

    dm_data = parse_result.value

    # Convert to layers
    try:
        layers = dm_to_layers(dm_data, group_by_classification=group_by_classification)
    except Exception as e:
        return Failure(
            error_type=ERROR_RECORD_PARSE,
            message=f"Failed to create layers: {str(e)}",
            context={"file": dm_file_path, "error": str(e)},
        )

    if not layers:
        return Failure(
            error_type=ERROR_RECORD_PARSE,
            message="No layers created from DM file",
            context={"file": dm_file_path},
        )

    # Save to GeoPackage
    success = save_layers_to_geopackage(layers, output_path)

    if success:
        return Success(value=output_path)
    else:
        return Failure(
            error_type=ERROR_RECORD_PARSE,
            message="Failed to save GeoPackage",
            context={"file": dm_file_path, "output": output_path},
        )


# Convenience accessors for DMData
def get_map_sheet_info(dm_data: DMData) -> dict:
    """Get map sheet information from DMData.

    Args:
        dm_data: Parsed DM data

    Returns:
        Dictionary with map sheet details
    """
    if not dm_data.map_sheets:
        return {}

    sheet = dm_data.map_sheets[0]
    return {
        "sheet_id": sheet.sheet_id,
        "sheet_name": sheet.sheet_name,
        "map_info_level": sheet.map_info_level,
        "bounds": sheet.bounds,
        "coordinate_unit": sheet.coordinate_unit,
    }


def get_element_summary(dm_data: DMData) -> dict:
    """Get summary of elements in DMData.

    Args:
        dm_data: Parsed DM data

    Returns:
        Dictionary with element counts by type
    """
    summary: dict[str, int] = {}

    for group in dm_data.elements:
        for element in group.elements:
            data_type = element.data_type
            summary[data_type] = summary.get(data_type, 0) + 1

    return summary


def get_crs_info(dm_data: DMData) -> dict:
    """Get coordinate reference system information from DMData.

    Args:
        dm_data: Parsed DM data

    Returns:
        Dictionary with CRS details
    """
    return {
        "crs_code": dm_data.crs_code,
        "epsg": f"EPSG:{dm_data.crs_code}",
        "datum": dm_data.datum,
        "coordinate_system": dm_data.index.coordinate_system,
    }
