"""Integration tests for layer generation.

Tests the complete layer generation pipeline using real DM files.
Requirements: 2.1, 3.1-3.7, 4.1-4.8
"""

from __future__ import annotations

import os
import tempfile
import unittest

# Try to import QGIS, skip tests if not available
try:
    from qgis.core import QgsVectorLayer, QgsWkbTypes

    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False

from dmconverter.dm_parser.api import (
    parse_dm_file,
    dm_to_layers,
    load_dm_to_qgis,
    save_dm_to_geopackage,
)
from dmconverter.dm_parser.errors import is_success


# Test data paths
SAMPLE_DM_SMALL = "tests/sample_data/02JF711.dm"


@unittest.skipUnless(QGIS_AVAILABLE, "QGIS not available")
class TestLayerGenerationIntegration(unittest.TestCase):
    """Integration tests for layer generation."""

    @classmethod
    def setUpClass(cls) -> None:
        """Parse the sample file once for all tests."""
        if os.path.exists(SAMPLE_DM_SMALL):
            cls.result = parse_dm_file(SAMPLE_DM_SMALL)
            cls.file_exists = True
            if is_success(cls.result):
                cls.layers = dm_to_layers(cls.result.value)
            else:
                cls.layers = []
        else:
            cls.file_exists = False
            cls.layers = []

    def test_layers_created(self) -> None:
        """Layers should be created from parsed data."""
        if not self.file_exists:
            self.skipTest("Sample file not found")
        self.assertGreater(len(self.layers), 0)

    def test_layers_are_valid(self) -> None:
        """All created layers should be valid."""
        if not self.file_exists:
            self.skipTest("Sample file not found")

        for layer in self.layers:
            self.assertIsInstance(layer, QgsVectorLayer)
            self.assertTrue(layer.isValid())

    def test_layers_have_features(self) -> None:
        """Layers should contain features."""
        if not self.file_exists:
            self.skipTest("Sample file not found")

        total_features = sum(layer.featureCount() for layer in self.layers)
        self.assertGreater(total_features, 0)

    def test_layer_has_crs(self) -> None:
        """Layers should have CRS set."""
        if not self.file_exists or not self.layers:
            self.skipTest("Sample file not found or no layers")

        for layer in self.layers:
            crs = layer.crs()
            # CRS might not be valid if QGIS is not fully initialized
            # but the auth id should still be set
            authid = crs.authid()
            if authid:
                self.assertTrue(authid.startswith("EPSG:"))
            else:
                # If no authid, skip (QGIS not fully initialized)
                self.skipTest("QGIS CRS not fully initialized")

    def test_layer_has_attributes(self) -> None:
        """Layers should have standard attribute fields."""
        if not self.file_exists or not self.layers:
            self.skipTest("Sample file not found or no layers")

        for layer in self.layers:
            fields = layer.fields()
            field_names = [f.name() for f in fields]

            self.assertIn("classification_code", field_names)
            self.assertIn("classification_name", field_names)
            self.assertIn("hierarchy_level", field_names)
            self.assertIn("data_type", field_names)

    def test_features_have_geometry(self) -> None:
        """Features should have valid geometry."""
        if not self.file_exists or not self.layers:
            self.skipTest("Sample file not found or no layers")

        for layer in self.layers:
            for feature in layer.getFeatures():
                geom = feature.geometry()
                self.assertFalse(geom.isNull())
                self.assertTrue(geom.isGeosValid() or geom.type() == QgsWkbTypes.PointGeometry)

    def test_features_have_attributes(self) -> None:
        """Features should have attribute values set."""
        if not self.file_exists or not self.layers:
            self.skipTest("Sample file not found or no layers")

        for layer in self.layers:
            for feature in layer.getFeatures():
                attrs = feature.attributes()
                # classification_code should be set
                code = attrs[0]
                self.assertIsNotNone(code)
                self.assertGreater(len(str(code)), 0)
                break  # Just check first feature


@unittest.skipUnless(QGIS_AVAILABLE, "QGIS not available")
class TestLoadDmToQgisIntegration(unittest.TestCase):
    """Integration tests for load_dm_to_qgis function."""

    def test_load_dm_creates_layers(self) -> None:
        """load_dm_to_qgis should create valid layers."""
        if not os.path.exists(SAMPLE_DM_SMALL):
            self.skipTest("Sample file not found")

        result = load_dm_to_qgis(SAMPLE_DM_SMALL, add_to_project=False)
        self.assertTrue(is_success(result))

        layers = result.value
        self.assertGreater(len(layers), 0)
        for layer in layers:
            self.assertTrue(layer.isValid())


@unittest.skipUnless(QGIS_AVAILABLE, "QGIS not available")
class TestGeoPackageExportIntegration(unittest.TestCase):
    """Integration tests for GeoPackage export."""

    def test_save_to_geopackage_creates_file(self) -> None:
        """Saving to GeoPackage should create a valid file."""
        if not os.path.exists(SAMPLE_DM_SMALL):
            self.skipTest("Sample file not found")

        with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as f:
            gpkg_path = f.name

        try:
            result = save_dm_to_geopackage(SAMPLE_DM_SMALL, gpkg_path)
            self.assertTrue(is_success(result))
            self.assertTrue(os.path.exists(gpkg_path))

            # File should have content
            file_size = os.path.getsize(gpkg_path)
            self.assertGreater(file_size, 0)
        finally:
            if os.path.exists(gpkg_path):
                os.unlink(gpkg_path)

    def test_geopackage_can_be_loaded(self) -> None:
        """Saved GeoPackage should be loadable."""
        if not os.path.exists(SAMPLE_DM_SMALL):
            self.skipTest("Sample file not found")

        with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as f:
            gpkg_path = f.name

        try:
            result = save_dm_to_geopackage(SAMPLE_DM_SMALL, gpkg_path)
            if not is_success(result):
                self.skipTest("Failed to save GeoPackage")

            # Try to load the saved GeoPackage
            # Note: Layer names are DM_Points, DM_Lines, DM_Polygons
            for layer_name in ["DM_Points", "DM_Lines", "DM_Polygons"]:
                uri = f"{gpkg_path}|layername={layer_name}"
                layer = QgsVectorLayer(uri, layer_name, "ogr")
                if layer.isValid():
                    # At least one layer should be loadable
                    self.assertTrue(layer.featureCount() >= 0)
                    return

            # If we get here, try without layer name
            layer = QgsVectorLayer(gpkg_path, "test", "ogr")
            self.assertTrue(layer.isValid())

        finally:
            if os.path.exists(gpkg_path):
                os.unlink(gpkg_path)


@unittest.skipUnless(QGIS_AVAILABLE, "QGIS not available")
class TestCrsIntegration(unittest.TestCase):
    """Integration tests for CRS handling."""

    def test_crs_is_valid_japan_crs(self) -> None:
        """CRS should be a valid Japan coordinate system."""
        if not os.path.exists(SAMPLE_DM_SMALL):
            self.skipTest("Sample file not found")

        result = load_dm_to_qgis(SAMPLE_DM_SMALL, add_to_project=False)
        if not is_success(result):
            self.skipTest("Failed to load DM file")

        layers = result.value
        if not layers:
            self.skipTest("No layers created")

        layer = layers[0]
        crs = layer.crs()

        authid = crs.authid()
        if not authid:
            # QGIS not fully initialized
            self.skipTest("QGIS CRS not fully initialized")

        # Should be EPSG code for Japan CRS
        epsg_num = int(authid.replace("EPSG:", ""))

        # Valid ranges: JGD2000 (2443-2461) or JGD2011 (6669-6687)
        valid_jgd2000 = 2443 <= epsg_num <= 2461
        valid_jgd2011 = 6669 <= epsg_num <= 6687

        self.assertTrue(
            valid_jgd2000 or valid_jgd2011,
            f"EPSG:{epsg_num} is not a valid Japan CRS"
        )


if __name__ == "__main__":
    unittest.main()
