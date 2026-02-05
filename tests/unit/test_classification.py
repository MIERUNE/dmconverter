"""Unit tests for classification code mapping functions.

TDD Red phase: Test classification code mapping.
Requirements: 5.1, 5.2, 5.3, 5.4
"""

from __future__ import annotations

import unittest

from dmconverter.dm_parser.classification import (
    get_classification_name,
    get_classification_info,
    get_codes_by_category,
    CLASSIFICATION_TABLE,
    CATEGORY_ADMINISTRATIVE,
    CATEGORY_TRANSPORT,
    CATEGORY_BUILDING,
    CATEGORY_WATER,
    CATEGORY_TOPOGRAPHY,
    CATEGORY_VEGETATION,
    CATEGORY_OTHER,
)


class TestClassificationTable(unittest.TestCase):
    """Tests for classification table constants."""

    def test_classification_table_exists(self) -> None:
        """Classification table should be defined."""
        self.assertIsInstance(CLASSIFICATION_TABLE, dict)
        self.assertGreater(len(CLASSIFICATION_TABLE), 0)

    def test_classification_table_has_common_codes(self) -> None:
        """Classification table should have common DM codes."""
        # 行政界
        self.assertIn("1100", CLASSIFICATION_TABLE)  # 境界
        # 道路
        self.assertIn("2100", CLASSIFICATION_TABLE)  # 道路縁
        # 建物
        self.assertIn("3000", CLASSIFICATION_TABLE)  # 建物

    def test_category_constants_defined(self) -> None:
        """Category constants should be defined."""
        self.assertEqual(CATEGORY_ADMINISTRATIVE, "行政界")
        self.assertEqual(CATEGORY_TRANSPORT, "交通施設")
        self.assertEqual(CATEGORY_BUILDING, "建物")
        self.assertEqual(CATEGORY_WATER, "水部")
        self.assertEqual(CATEGORY_TOPOGRAPHY, "地形")
        self.assertEqual(CATEGORY_VEGETATION, "植生")
        self.assertEqual(CATEGORY_OTHER, "その他")


class TestGetClassificationName(unittest.TestCase):
    """Tests for get_classification_name function."""

    def test_get_name_known_code(self) -> None:
        """Get name for known classification code."""
        name = get_classification_name("1100")
        self.assertIsInstance(name, str)
        self.assertGreater(len(name), 0)

    def test_get_name_unknown_code_returns_code(self) -> None:
        """Get name for unknown code returns the code itself."""
        name = get_classification_name("99999")
        self.assertEqual(name, "99999")

    def test_get_name_with_subcode(self) -> None:
        """Get name for code with subcode."""
        name = get_classification_name("21103")
        self.assertIsInstance(name, str)


class TestGetClassificationInfo(unittest.TestCase):
    """Tests for get_classification_info function."""

    def test_get_info_known_code(self) -> None:
        """Get info for known classification code."""
        info = get_classification_info("2100")
        self.assertIn("name", info)
        self.assertIn("category", info)

    def test_get_info_returns_category(self) -> None:
        """Info should include category."""
        info = get_classification_info("2100")  # 道路縁
        self.assertEqual(info["category"], CATEGORY_TRANSPORT)

    def test_get_info_unknown_code(self) -> None:
        """Get info for unknown code returns code as name."""
        info = get_classification_info("99999")
        self.assertEqual(info["name"], "99999")
        self.assertEqual(info["category"], CATEGORY_OTHER)


class TestGetCodesByCategory(unittest.TestCase):
    """Tests for get_codes_by_category function."""

    def test_get_transport_codes(self) -> None:
        """Get codes for transport category."""
        codes = get_codes_by_category(CATEGORY_TRANSPORT)
        self.assertIsInstance(codes, list)
        self.assertIn("2100", codes)

    def test_get_building_codes(self) -> None:
        """Get codes for building category."""
        codes = get_codes_by_category(CATEGORY_BUILDING)
        self.assertIsInstance(codes, list)
        self.assertIn("3000", codes)

    def test_get_unknown_category_returns_empty(self) -> None:
        """Get codes for unknown category returns empty list."""
        codes = get_codes_by_category("未知のカテゴリ")
        self.assertEqual(codes, [])


if __name__ == "__main__":
    unittest.main()
