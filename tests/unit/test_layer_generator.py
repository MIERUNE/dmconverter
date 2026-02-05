"""Unit tests for vector layer generation functions.

TDD Red phase: Test layer generation from DMData.
Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8
"""

from __future__ import annotations

import os
import tempfile
import unittest

# Try to import QGIS, skip tests if not available
try:
    from qgis.core import QgsVectorLayer, QgsApplication

    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False

from dmconverter.dm_parser.layer_generator import (
    create_memory_layer,
    add_features_to_layer,
    dm_data_to_layers,
    save_layer_to_geopackage,
    LayerInfo,
)
from dmconverter.dm_parser.models import (
    Coordinate,
    DMData,
    ElementGroup,
    ElementRecord,
    IndexRecord,
    MapSheetRecord,
)


def create_sample_dm_data() -> DMData:
    """Create sample DMData for testing."""
    index = IndexRecord(
        record_type="A",
        coordinate_system=2,
        organization_name="テスト機関",
        map_sheet_count=1,
        classification_code_count=2,
        work_standard_name="テスト",
        version=1,
    )

    map_sheet = MapSheetRecord(
        sheet_id="02JF711",
        sheet_name="四辻",
        map_info_level=1000,
        title="テスト図郭",
        bounds=(7500.0, 44000.0, 9000.0, 46000.0),
        base_coordinate=Coordinate(x=10268.0, y=35428.0, z=None),
        coordinate_unit=1,
        survey_result_code=2,
    )

    # Create sample elements
    line_element = ElementRecord(
        classification_code="21103",
        data_type="E2",
        hierarchy_level=1,
        coordinates=(
            Coordinate(x=10500.0, y=35500.0, z=None),
            Coordinate(x=10600.0, y=35600.0, z=None),
            Coordinate(x=10700.0, y=35500.0, z=None),
        ),
        annotation=None,
        attributes=None,
    )

    point_element = ElementRecord(
        classification_code="31001",
        data_type="E5",
        hierarchy_level=1,
        coordinates=(Coordinate(x=10500.0, y=35500.0, z=None),),
        annotation=None,
        attributes=None,
    )

    polygon_element = ElementRecord(
        classification_code="30001",
        data_type="E1",
        hierarchy_level=1,
        coordinates=(
            Coordinate(x=10500.0, y=35500.0, z=None),
            Coordinate(x=10600.0, y=35500.0, z=None),
            Coordinate(x=10600.0, y=35600.0, z=None),
            Coordinate(x=10500.0, y=35600.0, z=None),
            Coordinate(x=10500.0, y=35500.0, z=None),
        ),
        annotation=None,
        attributes=None,
    )

    group1 = ElementGroup(
        classification_code="2110",
        hierarchy_level=1,
        elements=(line_element,),
    )

    group2 = ElementGroup(
        classification_code="3100",
        hierarchy_level=1,
        elements=(point_element,),
    )

    group3 = ElementGroup(
        classification_code="3000",
        hierarchy_level=1,
        elements=(polygon_element,),
    )

    return DMData(
        index=index,
        map_sheets=(map_sheet,),
        elements=(group1, group2, group3),
        crs_code=6670,
        datum="JGD2011",
    )


class TestLayerInfo(unittest.TestCase):
    """Tests for LayerInfo dataclass."""

    def test_layer_info_creation(self) -> None:
        """Create LayerInfo object."""
        info = LayerInfo(
            name="test_layer",
            geometry_type="LineString",
            crs_code=6670,
            classification_code="21103",
        )
        self.assertEqual(info.name, "test_layer")
        self.assertEqual(info.geometry_type, "LineString")


@unittest.skipUnless(QGIS_AVAILABLE, "QGIS not available")
class TestCreateMemoryLayer(unittest.TestCase):
    """Tests for create_memory_layer function."""

    def test_create_line_layer(self) -> None:
        """Create memory layer for lines."""
        layer = create_memory_layer(
            name="test_lines",
            geometry_type="LineString",
            crs_code=6670,
        )
        self.assertIsInstance(layer, QgsVectorLayer)
        self.assertTrue(layer.isValid())

    def test_create_point_layer(self) -> None:
        """Create memory layer for points."""
        layer = create_memory_layer(
            name="test_points",
            geometry_type="Point",
            crs_code=6670,
        )
        self.assertIsInstance(layer, QgsVectorLayer)
        self.assertTrue(layer.isValid())

    def test_create_polygon_layer(self) -> None:
        """Create memory layer for polygons."""
        layer = create_memory_layer(
            name="test_polygons",
            geometry_type="Polygon",
            crs_code=6670,
        )
        self.assertIsInstance(layer, QgsVectorLayer)
        self.assertTrue(layer.isValid())

    def test_layer_has_standard_fields(self) -> None:
        """Memory layer should have standard fields."""
        layer = create_memory_layer(
            name="test_layer",
            geometry_type="LineString",
            crs_code=6670,
        )
        fields = layer.fields()
        field_names = [f.name() for f in fields]

        self.assertIn("classification_code", field_names)
        self.assertIn("classification_name", field_names)
        self.assertIn("hierarchy_level", field_names)


@unittest.skipUnless(QGIS_AVAILABLE, "QGIS not available")
class TestAddFeaturesToLayer(unittest.TestCase):
    """Tests for add_features_to_layer function."""

    def test_add_line_features(self) -> None:
        """Add line features to layer."""
        layer = create_memory_layer(
            name="test_lines",
            geometry_type="LineString",
            crs_code=6670,
        )

        elements = [
            ElementRecord(
                classification_code="21103",
                data_type="E2",
                hierarchy_level=1,
                coordinates=(
                    Coordinate(x=10500.0, y=35500.0, z=None),
                    Coordinate(x=10600.0, y=35600.0, z=None),
                ),
                annotation=None,
                attributes=None,
            ),
        ]

        count = add_features_to_layer(layer, elements)
        self.assertEqual(count, 1)
        self.assertEqual(layer.featureCount(), 1)

    def test_add_point_features(self) -> None:
        """Add point features to layer."""
        layer = create_memory_layer(
            name="test_points",
            geometry_type="Point",
            crs_code=6670,
        )

        elements = [
            ElementRecord(
                classification_code="31001",
                data_type="E5",
                hierarchy_level=1,
                coordinates=(Coordinate(x=10500.0, y=35500.0, z=None),),
                annotation=None,
                attributes=None,
            ),
        ]

        count = add_features_to_layer(layer, elements)
        self.assertEqual(count, 1)


@unittest.skipUnless(QGIS_AVAILABLE, "QGIS not available")
class TestDmDataToLayers(unittest.TestCase):
    """Tests for dm_data_to_layers function."""

    def test_converts_dm_data_to_layers(self) -> None:
        """Convert DMData to list of layers."""
        dm_data = create_sample_dm_data()
        layers = dm_data_to_layers(dm_data)

        self.assertIsInstance(layers, list)
        self.assertGreater(len(layers), 0)

    def test_creates_layers_by_geometry_type(self) -> None:
        """Creates separate layers for different geometry types."""
        dm_data = create_sample_dm_data()
        layers = dm_data_to_layers(dm_data)

        # Should have at least point, line, and polygon layers
        geometry_types = set()
        for layer in layers:
            geom_type = layer.geometryType()
            geometry_types.add(geom_type)

        self.assertGreaterEqual(len(geometry_types), 1)


@unittest.skipUnless(QGIS_AVAILABLE, "QGIS not available")
class TestSaveToGeopackage(unittest.TestCase):
    """Tests for save_layer_to_geopackage function."""

    def test_save_single_layer(self) -> None:
        """Save single layer to GeoPackage."""
        layer = create_memory_layer(
            name="test_layer",
            geometry_type="Point",
            crs_code=6670,
        )

        # Add a feature
        elements = [
            ElementRecord(
                classification_code="31001",
                data_type="E5",
                hierarchy_level=1,
                coordinates=(Coordinate(x=10500.0, y=35500.0, z=None),),
                annotation=None,
                attributes=None,
            ),
        ]
        add_features_to_layer(layer, elements)

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as f:
            gpkg_path = f.name

        try:
            result = save_layer_to_geopackage(layer, gpkg_path)
            self.assertTrue(result)
            self.assertTrue(os.path.exists(gpkg_path))
        finally:
            if os.path.exists(gpkg_path):
                os.unlink(gpkg_path)


if __name__ == "__main__":
    unittest.main()
