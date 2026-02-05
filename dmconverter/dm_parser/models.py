"""Data models for DM Parser.

This module defines all data structures used for representing
parsed DM file data. All dataclasses are frozen (immutable) to
ensure data integrity and support functional programming patterns.

Data Types:
    - Coordinate: 2D/3D coordinate values
    - IndexRecord: File metadata from index records
    - MapSheetRecord: Map sheet boundary and coordinate info
    - AnnotationData: Text annotation properties
    - ElementRecord: Geographic feature data
    - ElementGroup: Grouped elements by classification
    - DMData: Complete parsed file structure
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Type alias for geodetic datum
GeodeticDatum = Literal["JGD2011", "JGD2000"]


@dataclass(frozen=True)
class Coordinate:
    """Immutable coordinate value.

    Represents a 2D or 3D coordinate point. Z value is optional
    for 2D coordinates.

    Attributes:
        x: X coordinate value (easting in meters after normalization)
        y: Y coordinate value (northing in meters after normalization)
        z: Z coordinate value (height in meters), None for 2D
    """

    x: float
    y: float
    z: float | None = None


@dataclass(frozen=True)
class IndexRecord:
    """Index record data from DM file header.

    Contains metadata about the DM file including coordinate system,
    organization, and version information.

    Attributes:
        record_type: Record type identifier (always "A")
        coordinate_system: Plane rectangular coordinate system code (1-19)
        organization_name: Name of the surveying organization
        map_sheet_count: Number of map sheets in the file
        classification_code_count: Number of classification codes used
        work_standard_name: Name of the survey standard used
        version: File format version number
    """

    record_type: Literal["A"]
    coordinate_system: int
    organization_name: str
    map_sheet_count: int
    classification_code_count: int
    work_standard_name: str
    version: int


@dataclass(frozen=True)
class MapSheetRecord:
    """Map sheet record data.

    Contains information about a single map sheet including its
    identifier, bounds, coordinate system settings, and survey metadata.

    Attributes:
        sheet_id: Unique identifier for the map sheet
        sheet_name: Human-readable name of the map sheet
        map_info_level: Map information level (500, 1000, 2500, etc.)
        title: Title or description of the map sheet
        bounds: Bounding box as (min_x, min_y, max_x, max_y)
        base_coordinate: Lower-left corner coordinate for relative-to-absolute conversion
        coordinate_unit: Unit code (1=m, 10=cm, 999=mm)
        survey_result_code: Geodetic datum code (0,1=JGD2000, 2=JGD2011)
    """

    sheet_id: str
    sheet_name: str
    map_info_level: int
    title: str
    bounds: tuple[float, float, float, float]
    base_coordinate: Coordinate
    coordinate_unit: int
    survey_result_code: int


@dataclass(frozen=True)
class AnnotationData:
    """Annotation (text) data for E7 elements.

    Contains properties for rendering text annotations on the map.

    Attributes:
        text: The annotation text content
        orientation: Text direction ("horizontal" or "vertical")
        direction: Text rotation angle in degrees
        font_size: Font size in 0.1mm units
        char_spacing: Character spacing in 0.1mm units
    """

    text: str
    orientation: Literal["horizontal", "vertical"]
    direction: float
    font_size: float
    char_spacing: float


@dataclass(frozen=True)
class ElementRecord:
    """Element record data representing a geographic feature.

    Contains all information for a single geographic feature including
    classification, geometry type, coordinates, and optional annotation
    or attribute data.

    Attributes:
        classification_code: Classification code (e.g., "21 01" for road edge)
        data_type: Element type (E1=polygon, E2=line, E3=circle, E4=arc,
                   E5=point, E6=direction, E7=annotation, E8=attribute)
        hierarchy_level: Hierarchy level within the classification
        coordinates: Tuple of coordinate points defining the geometry
        annotation: Optional annotation data for E7 elements
        attributes: Optional user-defined attributes as key-value pairs
    """

    classification_code: str
    data_type: Literal["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"]
    hierarchy_level: int
    coordinates: tuple[Coordinate, ...]
    annotation: AnnotationData | None = None
    attributes: tuple[tuple[str, str], ...] | None = None


@dataclass(frozen=True)
class ElementGroup:
    """Group of elements with the same classification code.

    Organizes elements by their classification code and hierarchy level
    for easier processing and layer generation.

    Attributes:
        classification_code: Classification code for all elements in the group
        hierarchy_level: Hierarchy level for the group
        elements: Tuple of element records in this group
    """

    classification_code: str
    hierarchy_level: int
    elements: tuple[ElementRecord, ...]


@dataclass(frozen=True)
class DMData:
    """Complete parsed DM file data structure.

    The root data structure containing all parsed information from
    a DM file. Includes index data, map sheet records, all elements,
    and coordinate reference system information.

    Attributes:
        index: Index record with file metadata
        map_sheets: Tuple of map sheet records
        elements: Tuple of element groups
        crs_code: EPSG code for the coordinate reference system
        datum: Geodetic datum ("JGD2011" or "JGD2000")
    """

    index: IndexRecord
    map_sheets: tuple[MapSheetRecord, ...]
    elements: tuple[ElementGroup, ...]
    crs_code: int
    datum: GeodeticDatum
