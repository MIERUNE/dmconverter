"""Vector layer generation functions for DM files.

This module provides functions to convert parsed DMData into
QGIS vector layers for visualization and analysis.

Functions:
    - create_memory_layer: Create an in-memory QGIS vector layer
    - add_features_to_layer: Add element records as features
    - dm_data_to_layers: Convert DMData to list of layers
    - save_layer_to_geopackage: Save layer to GeoPackage file
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

# Try to import QGIS modules
try:
    from qgis.core import (
        QgsCoordinateReferenceSystem,
        QgsFeature,
        QgsField,
        QgsFields,
        QgsGeometry,
        QgsPointXY,
        QgsVectorFileWriter,
        QgsVectorLayer,
        QgsWkbTypes,
    )
    from qgis.PyQt.QtCore import QVariant

    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False

from dmconverter.dm_parser.classification import get_classification_name
from dmconverter.dm_parser.geometry import (
    convert_element_to_geometry,
    coordinates_to_point_list,
)
from dmconverter.dm_parser.models import DMData, ElementRecord


@dataclass(frozen=True)
class LayerInfo:
    """Information about a generated layer.

    Attributes:
        name: Layer name
        geometry_type: Geometry type (Point, LineString, Polygon)
        crs_code: EPSG code for the coordinate reference system
        classification_code: Classification code for the elements
    """

    name: str
    geometry_type: Literal["Point", "LineString", "Polygon", "MultiPoint"]
    crs_code: int
    classification_code: str


def create_memory_layer(
    name: str,
    geometry_type: str,
    crs_code: int,
) -> "QgsVectorLayer":
    """Create an in-memory QGIS vector layer.

    Creates a memory provider layer with standard fields for
    DM element data.

    Args:
        name: Layer name
        geometry_type: Geometry type (Point, LineString, Polygon)
        crs_code: EPSG code for the coordinate reference system

    Returns:
        QgsVectorLayer configured for the geometry type

    Raises:
        ImportError: If QGIS modules are not available
    """
    if not QGIS_AVAILABLE:
        raise ImportError("QGIS modules are not available")

    # Create layer URI
    uri = f"{geometry_type}?crs=EPSG:{crs_code}"

    # Create the layer
    layer = QgsVectorLayer(uri, name, "memory")

    if not layer.isValid():
        raise ValueError(f"Failed to create layer: {name}")

    # Add standard fields
    provider = layer.dataProvider()

    fields = QgsFields()
    fields.append(QgsField("classification_code", QVariant.String))
    fields.append(QgsField("classification_name", QVariant.String))
    fields.append(QgsField("hierarchy_level", QVariant.Int))
    fields.append(QgsField("data_type", QVariant.String))

    provider.addAttributes(fields)
    layer.updateFields()

    return layer


def add_features_to_layer(
    layer: "QgsVectorLayer",
    elements: Sequence[ElementRecord],
) -> int:
    """Add element records as features to a layer.

    Converts ElementRecord objects to QgsFeature objects and
    adds them to the layer.

    Args:
        layer: Target QGIS vector layer
        elements: Sequence of ElementRecord objects to add

    Returns:
        Number of features successfully added
    """
    if not QGIS_AVAILABLE:
        raise ImportError("QGIS modules are not available")

    provider = layer.dataProvider()
    features = []

    for element in elements:
        # Convert coordinates to geometry
        if not element.coordinates:
            continue

        geom_dict = convert_element_to_geometry(
            element.data_type,
            element.coordinates,
        )

        # Create QGIS geometry based on type
        geom_type = geom_dict.get("type", "")

        if geom_type == "Point":
            coords = geom_dict.get("coordinates", (0, 0))
            if len(coords) >= 2:
                point = QgsPointXY(coords[0], coords[1])
                geometry = QgsGeometry.fromPointXY(point)
            else:
                continue

        elif geom_type == "LineString":
            coords = geom_dict.get("coordinates", [])
            if len(coords) >= 2:
                points = [QgsPointXY(c[0], c[1]) for c in coords]
                geometry = QgsGeometry.fromPolylineXY(points)
            else:
                continue

        elif geom_type == "Polygon":
            rings = geom_dict.get("coordinates", [[]])
            if rings and len(rings[0]) >= 3:
                points = [QgsPointXY(c[0], c[1]) for c in rings[0]]
                geometry = QgsGeometry.fromPolygonXY([points])
            else:
                continue

        elif geom_type in ("Circle", "Arc"):
            # Use polygon approximation for circles and arcs
            coords = geom_dict.get("coordinates", [[]])
            if coords:
                if isinstance(coords[0], list):
                    # Nested list (polygon)
                    points = [QgsPointXY(c[0], c[1]) for c in coords[0]]
                    geometry = QgsGeometry.fromPolygonXY([points])
                else:
                    # Flat list (line)
                    points = [QgsPointXY(c[0], c[1]) for c in coords]
                    geometry = QgsGeometry.fromPolylineXY(points)
            else:
                continue

        elif geom_type == "None":
            # E8 attribute - no geometry
            continue

        else:
            continue

        # Create feature
        feature = QgsFeature()
        feature.setGeometry(geometry)

        # Set attributes
        classification_name = get_classification_name(element.classification_code)
        feature.setAttributes(
            [
                element.classification_code,
                classification_name,
                element.hierarchy_level,
                element.data_type,
            ]
        )

        features.append(feature)

    # Add features in batch
    if features:
        success, _ = provider.addFeatures(features)
        if success:
            layer.updateExtents()
            return len(features)

    return 0


def _get_geometry_category(data_type: str) -> str:
    """Get geometry category for a data type.

    Args:
        data_type: Element data type (E1-E8)

    Returns:
        Geometry category: 'Point', 'Line', or 'Polygon'
    """
    if data_type in ("E5", "E6", "E7"):
        return "Point"
    elif data_type in ("E2", "E4"):
        return "Line"
    elif data_type in ("E1", "E3"):
        return "Polygon"
    return "Line"  # Default


def _get_qgis_geometry_type(category: str) -> str:
    """Get QGIS geometry type string for a category.

    Args:
        category: Geometry category

    Returns:
        QGIS geometry type string
    """
    if category == "Point":
        return "Point"
    elif category == "Line":
        return "LineString"
    elif category == "Polygon":
        return "Polygon"
    return "LineString"


def dm_data_to_layers(
    dm_data: DMData,
    group_by_classification: bool = False,
) -> list["QgsVectorLayer"]:
    """Convert DMData to list of QGIS vector layers.

    Creates separate layers for different geometry types (point, line, polygon).
    When group_by_classification is True, creates separate layers for each
    2-digit classification code prefix AND geometry type combination.

    Layer naming:
        - group_by_classification=False: DM_Points, DM_Lines, DM_Polygons
        - group_by_classification=True: DM_{code}_{geom} (e.g., DM_11_Line, DM_30_Point)

    Args:
        dm_data: Parsed DM data
        group_by_classification: If True, create separate layer for each
                                 2-digit classification code prefix

    Returns:
        List of QgsVectorLayer objects
    """
    if not QGIS_AVAILABLE:
        raise ImportError("QGIS modules are not available")

    crs_code = dm_data.crs_code

    if group_by_classification:
        # Group by 2-digit classification prefix AND geometry type
        # Key: (2-digit prefix, geometry category)
        element_groups: dict[tuple[str, str], list[ElementRecord]] = {}

        for group in dm_data.elements:
            for element in group.elements:
                # Get 2-digit prefix (pad with 0 if needed)
                code = element.classification_code
                prefix = code[:2] if len(code) >= 2 else code.zfill(2)[:2]

                geom_category = _get_geometry_category(element.data_type)
                key = (prefix, geom_category)

                if key not in element_groups:
                    element_groups[key] = []
                element_groups[key].append(element)

        layers: list[QgsVectorLayer] = []

        # Create a layer for each group
        for (prefix, geom_category), elements in sorted(element_groups.items()):
            if not elements:
                continue

            layer_name = f"DM_{prefix}_{geom_category}"
            qgis_geom_type = _get_qgis_geometry_type(geom_category)

            layer = create_memory_layer(layer_name, qgis_geom_type, crs_code)
            add_features_to_layer(layer, elements)

            if layer.featureCount() > 0:
                layers.append(layer)

        return layers

    else:
        # Original behavior: group only by geometry type
        point_elements: list[ElementRecord] = []
        line_elements: list[ElementRecord] = []
        polygon_elements: list[ElementRecord] = []

        for group in dm_data.elements:
            for element in group.elements:
                geom_category = _get_geometry_category(element.data_type)
                if geom_category == "Point":
                    point_elements.append(element)
                elif geom_category == "Line":
                    line_elements.append(element)
                elif geom_category == "Polygon":
                    polygon_elements.append(element)

        layers = []

        # Create point layer
        if point_elements:
            point_layer = create_memory_layer("DM_Points", "Point", crs_code)
            add_features_to_layer(point_layer, point_elements)
            if point_layer.featureCount() > 0:
                layers.append(point_layer)

        # Create line layer
        if line_elements:
            line_layer = create_memory_layer("DM_Lines", "LineString", crs_code)
            add_features_to_layer(line_layer, line_elements)
            if line_layer.featureCount() > 0:
                layers.append(line_layer)

        # Create polygon layer
        if polygon_elements:
            polygon_layer = create_memory_layer("DM_Polygons", "Polygon", crs_code)
            add_features_to_layer(polygon_layer, polygon_elements)
            if polygon_layer.featureCount() > 0:
                layers.append(polygon_layer)

        return layers


def save_layer_to_geopackage(
    layer: "QgsVectorLayer",
    output_path: str,
    layer_name: str | None = None,
) -> bool:
    """Save a vector layer to a GeoPackage file.

    Args:
        layer: QgsVectorLayer to save
        output_path: Path for the output GeoPackage file
        layer_name: Optional layer name in the GeoPackage

    Returns:
        True if save was successful, False otherwise
    """
    if not QGIS_AVAILABLE:
        raise ImportError("QGIS modules are not available")

    if layer_name is None:
        layer_name = layer.name()

    # Save options
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = layer_name

    # Write the file
    error = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer,
        output_path,
        layer.transformContext(),
        options,
    )

    return error[0] == QgsVectorFileWriter.NoError


def save_layers_to_geopackage(
    layers: Sequence["QgsVectorLayer"],
    output_path: str,
) -> bool:
    """Save multiple layers to a single GeoPackage file.

    Args:
        layers: Sequence of QgsVectorLayer objects to save
        output_path: Path for the output GeoPackage file

    Returns:
        True if all layers were saved successfully, False otherwise
    """
    if not QGIS_AVAILABLE:
        raise ImportError("QGIS modules are not available")

    if not layers:
        return False

    # Save first layer (creates the file)
    first_layer = layers[0]
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = first_layer.name()

    error = QgsVectorFileWriter.writeAsVectorFormatV3(
        first_layer,
        output_path,
        first_layer.transformContext(),
        options,
    )

    if error[0] != QgsVectorFileWriter.NoError:
        return False

    # Append remaining layers
    for layer in layers[1:]:
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = layer.name()
        options.actionOnExistingFile = (
            QgsVectorFileWriter.CreateOrOverwriteLayer
        )

        error = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer,
            output_path,
            layer.transformContext(),
            options,
        )

        if error[0] != QgsVectorFileWriter.NoError:
            return False

    return True
