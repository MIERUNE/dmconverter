"""
Unit tests for DM Parser data models.

Tests cover all data types defined in the design:
- Coordinate
- IndexRecord
- MapSheetRecord
- AnnotationData
- ElementRecord
- ElementGroup
- DMData
"""

import unittest
from dataclasses import FrozenInstanceError
from typing import Literal

from dmconverter.dm_parser.models import (
    AnnotationData,
    Coordinate,
    DMData,
    ElementGroup,
    ElementRecord,
    GeodeticDatum,
    IndexRecord,
    MapSheetRecord,
)


class TestCoordinate(unittest.TestCase):
    """Tests for Coordinate dataclass."""

    def test_create_2d_coordinate(self) -> None:
        """Test creating a 2D coordinate without Z value."""
        coord = Coordinate(x=100.0, y=200.0)
        self.assertEqual(coord.x, 100.0)
        self.assertEqual(coord.y, 200.0)
        self.assertIsNone(coord.z)

    def test_create_3d_coordinate(self) -> None:
        """Test creating a 3D coordinate with Z value."""
        coord = Coordinate(x=100.0, y=200.0, z=50.0)
        self.assertEqual(coord.x, 100.0)
        self.assertEqual(coord.y, 200.0)
        self.assertEqual(coord.z, 50.0)

    def test_coordinate_is_immutable(self) -> None:
        """Test that Coordinate is frozen (immutable)."""
        coord = Coordinate(x=100.0, y=200.0)
        with self.assertRaises(FrozenInstanceError):
            coord.x = 300.0  # type: ignore[misc]

    def test_coordinate_equality(self) -> None:
        """Test that Coordinate supports equality comparison."""
        coord1 = Coordinate(x=100.0, y=200.0, z=50.0)
        coord2 = Coordinate(x=100.0, y=200.0, z=50.0)
        coord3 = Coordinate(x=100.0, y=200.0)
        self.assertEqual(coord1, coord2)
        self.assertNotEqual(coord1, coord3)


class TestIndexRecord(unittest.TestCase):
    """Tests for IndexRecord dataclass."""

    def test_create_index_record(self) -> None:
        """Test creating an IndexRecord."""
        record = IndexRecord(
            record_type="A",
            coordinate_system=9,
            organization_name="国土地理院",
            map_sheet_count=1,
            classification_code_count=50,
            work_standard_name="公共測量標準図式",
            version=1,
        )
        self.assertEqual(record.record_type, "A")
        self.assertEqual(record.coordinate_system, 9)
        self.assertEqual(record.organization_name, "国土地理院")
        self.assertEqual(record.map_sheet_count, 1)
        self.assertEqual(record.classification_code_count, 50)
        self.assertEqual(record.work_standard_name, "公共測量標準図式")
        self.assertEqual(record.version, 1)

    def test_index_record_is_immutable(self) -> None:
        """Test that IndexRecord is frozen (immutable)."""
        record = IndexRecord(
            record_type="A",
            coordinate_system=9,
            organization_name="テスト",
            map_sheet_count=1,
            classification_code_count=10,
            work_standard_name="テスト",
            version=1,
        )
        with self.assertRaises(FrozenInstanceError):
            record.coordinate_system = 10  # type: ignore[misc]


class TestMapSheetRecord(unittest.TestCase):
    """Tests for MapSheetRecord dataclass."""

    def test_create_map_sheet_record(self) -> None:
        """Test creating a MapSheetRecord."""
        base_coord = Coordinate(x=-100000.0, y=50000.0)
        record = MapSheetRecord(
            sheet_id="02JF711",
            sheet_name="テスト図郭",
            map_info_level=2500,
            title="テスト地形図",
            bounds=(-100000.0, 50000.0, -99000.0, 51000.0),
            base_coordinate=base_coord,
            coordinate_unit=10,
            survey_result_code=2,
        )
        self.assertEqual(record.sheet_id, "02JF711")
        self.assertEqual(record.sheet_name, "テスト図郭")
        self.assertEqual(record.map_info_level, 2500)
        self.assertEqual(record.title, "テスト地形図")
        self.assertEqual(record.bounds, (-100000.0, 50000.0, -99000.0, 51000.0))
        self.assertEqual(record.base_coordinate, base_coord)
        self.assertEqual(record.coordinate_unit, 10)
        self.assertEqual(record.survey_result_code, 2)

    def test_map_sheet_record_is_immutable(self) -> None:
        """Test that MapSheetRecord is frozen (immutable)."""
        base_coord = Coordinate(x=0.0, y=0.0)
        record = MapSheetRecord(
            sheet_id="test",
            sheet_name="テスト",
            map_info_level=2500,
            title="テスト",
            bounds=(0.0, 0.0, 1000.0, 1000.0),
            base_coordinate=base_coord,
            coordinate_unit=10,
            survey_result_code=2,
        )
        with self.assertRaises(FrozenInstanceError):
            record.sheet_id = "modified"  # type: ignore[misc]


class TestAnnotationData(unittest.TestCase):
    """Tests for AnnotationData dataclass."""

    def test_create_annotation_data(self) -> None:
        """Test creating an AnnotationData."""
        annotation = AnnotationData(
            text="テスト注記",
            orientation="horizontal",
            direction=45.0,
            font_size=20.0,
            char_spacing=5.0,
        )
        self.assertEqual(annotation.text, "テスト注記")
        self.assertEqual(annotation.orientation, "horizontal")
        self.assertEqual(annotation.direction, 45.0)
        self.assertEqual(annotation.font_size, 20.0)
        self.assertEqual(annotation.char_spacing, 5.0)

    def test_annotation_orientation_types(self) -> None:
        """Test that orientation accepts both horizontal and vertical."""
        h_annotation = AnnotationData(
            text="横書き",
            orientation="horizontal",
            direction=0.0,
            font_size=10.0,
            char_spacing=1.0,
        )
        v_annotation = AnnotationData(
            text="縦書き",
            orientation="vertical",
            direction=90.0,
            font_size=10.0,
            char_spacing=1.0,
        )
        self.assertEqual(h_annotation.orientation, "horizontal")
        self.assertEqual(v_annotation.orientation, "vertical")


class TestElementRecord(unittest.TestCase):
    """Tests for ElementRecord dataclass."""

    def test_create_element_record_e2_line(self) -> None:
        """Test creating an E2 (line) ElementRecord."""
        coords = (
            Coordinate(x=100.0, y=200.0),
            Coordinate(x=150.0, y=250.0),
            Coordinate(x=200.0, y=200.0),
        )
        element = ElementRecord(
            classification_code="21 01",
            data_type="E2",
            hierarchy_level=1,
            coordinates=coords,
        )
        self.assertEqual(element.classification_code, "21 01")
        self.assertEqual(element.data_type, "E2")
        self.assertEqual(element.hierarchy_level, 1)
        self.assertEqual(len(element.coordinates), 3)
        self.assertIsNone(element.annotation)
        self.assertIsNone(element.attributes)

    def test_create_element_record_e7_annotation(self) -> None:
        """Test creating an E7 (annotation) ElementRecord."""
        coords = (Coordinate(x=100.0, y=200.0),)
        annotation = AnnotationData(
            text="道路名",
            orientation="horizontal",
            direction=0.0,
            font_size=15.0,
            char_spacing=2.0,
        )
        element = ElementRecord(
            classification_code="71 01",
            data_type="E7",
            hierarchy_level=1,
            coordinates=coords,
            annotation=annotation,
        )
        self.assertEqual(element.data_type, "E7")
        self.assertIsNotNone(element.annotation)
        self.assertEqual(element.annotation.text, "道路名")  # type: ignore[union-attr]

    def test_create_element_record_with_attributes(self) -> None:
        """Test creating an ElementRecord with user-defined attributes."""
        coords = (Coordinate(x=100.0, y=200.0),)
        attributes = (("name", "テスト"), ("type", "建物"))
        element = ElementRecord(
            classification_code="31 01",
            data_type="E5",
            hierarchy_level=2,
            coordinates=coords,
            attributes=attributes,
        )
        self.assertIsNotNone(element.attributes)
        self.assertEqual(len(element.attributes), 2)  # type: ignore[arg-type]
        self.assertEqual(element.attributes[0], ("name", "テスト"))  # type: ignore[index]

    def test_element_record_is_immutable(self) -> None:
        """Test that ElementRecord is frozen (immutable)."""
        coords = (Coordinate(x=100.0, y=200.0),)
        element = ElementRecord(
            classification_code="21 01",
            data_type="E2",
            hierarchy_level=1,
            coordinates=coords,
        )
        with self.assertRaises(FrozenInstanceError):
            element.classification_code = "21 02"  # type: ignore[misc]


class TestElementGroup(unittest.TestCase):
    """Tests for ElementGroup dataclass."""

    def test_create_element_group(self) -> None:
        """Test creating an ElementGroup."""
        coords = (Coordinate(x=100.0, y=200.0),)
        element1 = ElementRecord(
            classification_code="21 01",
            data_type="E2",
            hierarchy_level=1,
            coordinates=coords,
        )
        element2 = ElementRecord(
            classification_code="21 01",
            data_type="E5",
            hierarchy_level=1,
            coordinates=coords,
        )
        group = ElementGroup(
            classification_code="21 01",
            hierarchy_level=1,
            elements=(element1, element2),
        )
        self.assertEqual(group.classification_code, "21 01")
        self.assertEqual(group.hierarchy_level, 1)
        self.assertEqual(len(group.elements), 2)


class TestDMData(unittest.TestCase):
    """Tests for DMData dataclass."""

    def test_create_dm_data(self) -> None:
        """Test creating a complete DMData structure."""
        # Create index record
        index = IndexRecord(
            record_type="A",
            coordinate_system=9,
            organization_name="テスト機関",
            map_sheet_count=1,
            classification_code_count=10,
            work_standard_name="公共測量標準図式",
            version=1,
        )

        # Create map sheet record
        base_coord = Coordinate(x=-100000.0, y=50000.0)
        map_sheet = MapSheetRecord(
            sheet_id="02JF711",
            sheet_name="テスト図郭",
            map_info_level=2500,
            title="テスト",
            bounds=(-100000.0, 50000.0, -99000.0, 51000.0),
            base_coordinate=base_coord,
            coordinate_unit=10,
            survey_result_code=2,
        )

        # Create element group
        coords = (Coordinate(x=100.0, y=200.0),)
        element = ElementRecord(
            classification_code="21 01",
            data_type="E5",
            hierarchy_level=1,
            coordinates=coords,
        )
        group = ElementGroup(
            classification_code="21 01",
            hierarchy_level=1,
            elements=(element,),
        )

        # Create DMData
        dm_data = DMData(
            index=index,
            map_sheets=(map_sheet,),
            elements=(group,),
            crs_code=6677,
            datum="JGD2011",
        )

        self.assertEqual(dm_data.index.coordinate_system, 9)
        self.assertEqual(len(dm_data.map_sheets), 1)
        self.assertEqual(len(dm_data.elements), 1)
        self.assertEqual(dm_data.crs_code, 6677)
        self.assertEqual(dm_data.datum, "JGD2011")

    def test_dm_data_with_jgd2000(self) -> None:
        """Test creating DMData with JGD2000 datum."""
        index = IndexRecord(
            record_type="A",
            coordinate_system=9,
            organization_name="テスト",
            map_sheet_count=0,
            classification_code_count=0,
            work_standard_name="テスト",
            version=1,
        )
        base_coord = Coordinate(x=0.0, y=0.0)
        map_sheet = MapSheetRecord(
            sheet_id="test",
            sheet_name="テスト",
            map_info_level=2500,
            title="テスト",
            bounds=(0.0, 0.0, 1000.0, 1000.0),
            base_coordinate=base_coord,
            coordinate_unit=10,
            survey_result_code=0,
        )
        dm_data = DMData(
            index=index,
            map_sheets=(map_sheet,),
            elements=(),
            crs_code=2451,
            datum="JGD2000",
        )
        self.assertEqual(dm_data.datum, "JGD2000")
        self.assertEqual(dm_data.crs_code, 2451)


class TestGeodeticDatum(unittest.TestCase):
    """Tests for GeodeticDatum type alias."""

    def test_geodetic_datum_values(self) -> None:
        """Test that GeodeticDatum accepts JGD2011 and JGD2000."""
        # This is a type-level test; runtime validation is limited
        datum_jgd2011: GeodeticDatum = "JGD2011"
        datum_jgd2000: GeodeticDatum = "JGD2000"
        self.assertEqual(datum_jgd2011, "JGD2011")
        self.assertEqual(datum_jgd2000, "JGD2000")


if __name__ == "__main__":
    unittest.main()
