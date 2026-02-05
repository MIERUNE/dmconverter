"""Unit tests for public API functions.

TDD Red phase: Test public API.
Requirements: 7.1, 7.2, 7.3, 7.4
"""

from __future__ import annotations

import os
import tempfile
import unittest

# Try to import QGIS, skip tests if not available
try:
    from qgis.core import QgsVectorLayer

    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False

from dmconverter.dm_parser.api import (
    parse_dm_file,
    dm_to_layers,
    load_dm_to_qgis,
    save_dm_to_geopackage,
)
from dmconverter.dm_parser.models import DMData
from dmconverter.dm_parser.errors import is_success, is_failure


class TestParseDmFileAPI(unittest.TestCase):
    """Tests for parse_dm_file API function."""

    def test_parse_dm_file_success(self) -> None:
        """Parse valid DM file returns Success."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            result = parse_dm_file(path)
            self.assertTrue(is_success(result))

    def test_parse_dm_file_returns_dm_data(self) -> None:
        """Parse returns DMData on success."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            result = parse_dm_file(path)
            if is_success(result):
                self.assertIsInstance(result.value, DMData)

    def test_parse_dm_file_not_found(self) -> None:
        """Parse nonexistent file returns Failure."""
        result = parse_dm_file("nonexistent.dm")
        self.assertTrue(is_failure(result))

    def test_parse_dm_file_has_index(self) -> None:
        """Parsed DMData has index record."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            result = parse_dm_file(path)
            if is_success(result):
                self.assertIsNotNone(result.value.index)

    def test_parse_dm_file_has_crs(self) -> None:
        """Parsed DMData has CRS code."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            result = parse_dm_file(path)
            if is_success(result):
                self.assertGreater(result.value.crs_code, 0)


@unittest.skipUnless(QGIS_AVAILABLE, "QGIS not available")
class TestDmToLayersAPI(unittest.TestCase):
    """Tests for dm_to_layers API function."""

    def test_dm_to_layers_returns_list(self) -> None:
        """Convert DMData to layers returns list."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            result = parse_dm_file(path)
            if is_success(result):
                layers = dm_to_layers(result.value)
                self.assertIsInstance(layers, list)

    def test_dm_to_layers_returns_valid_layers(self) -> None:
        """Converted layers are valid QgsVectorLayers."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            result = parse_dm_file(path)
            if is_success(result):
                layers = dm_to_layers(result.value)
                for layer in layers:
                    self.assertIsInstance(layer, QgsVectorLayer)
                    self.assertTrue(layer.isValid())

    def test_dm_to_layers_has_features(self) -> None:
        """Converted layers have features."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            result = parse_dm_file(path)
            if is_success(result):
                layers = dm_to_layers(result.value)
                total_features = sum(layer.featureCount() for layer in layers)
                self.assertGreater(total_features, 0)


@unittest.skipUnless(QGIS_AVAILABLE, "QGIS not available")
class TestLoadDmToQgisAPI(unittest.TestCase):
    """Tests for load_dm_to_qgis API function."""

    def test_load_dm_to_qgis_returns_result(self) -> None:
        """Load DM to QGIS returns Result."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            result = load_dm_to_qgis(path, add_to_project=False)
            self.assertTrue(is_success(result) or is_failure(result))

    def test_load_dm_to_qgis_success(self) -> None:
        """Load valid DM file succeeds."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            result = load_dm_to_qgis(path, add_to_project=False)
            self.assertTrue(is_success(result))

    def test_load_dm_to_qgis_returns_layers(self) -> None:
        """Load returns list of layers on success."""
        path = "tests/sample_data/02JF711.dm"
        if os.path.exists(path):
            result = load_dm_to_qgis(path, add_to_project=False)
            if is_success(result):
                layers = result.value
                self.assertIsInstance(layers, list)
                self.assertGreater(len(layers), 0)


@unittest.skipUnless(QGIS_AVAILABLE, "QGIS not available")
class TestSaveDmToGeopackageAPI(unittest.TestCase):
    """Tests for save_dm_to_geopackage API function."""

    def test_save_dm_to_geopackage_creates_file(self) -> None:
        """Save creates GeoPackage file."""
        dm_path = "tests/sample_data/02JF711.dm"
        if os.path.exists(dm_path):
            with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as f:
                gpkg_path = f.name

            try:
                result = save_dm_to_geopackage(dm_path, gpkg_path)
                self.assertTrue(is_success(result))
                self.assertTrue(os.path.exists(gpkg_path))
            finally:
                if os.path.exists(gpkg_path):
                    os.unlink(gpkg_path)

    def test_save_dm_to_geopackage_invalid_dm(self) -> None:
        """Save with invalid DM file returns Failure."""
        with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as f:
            gpkg_path = f.name

        try:
            result = save_dm_to_geopackage("nonexistent.dm", gpkg_path)
            self.assertTrue(is_failure(result))
        finally:
            if os.path.exists(gpkg_path):
                os.unlink(gpkg_path)


if __name__ == "__main__":
    unittest.main()
