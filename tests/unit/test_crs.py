import unittest

from core.dmconverter.crs import get_epsg


class TestGetEpsg(unittest.TestCase):
    def test_system_1(self):
        """座標系1 → EPSG:6669"""
        self.assertEqual(get_epsg(1), 6669)

    def test_system_2(self):
        """座標系2 → EPSG:6670"""
        self.assertEqual(get_epsg(2), 6670)

    def test_system_19(self):
        """座標系19 → EPSG:6687"""
        self.assertEqual(get_epsg(19), 6687)

    def test_invalid_zero_raises(self):
        """座標系0は範囲外でValueError"""
        with self.assertRaises(ValueError):
            get_epsg(0)

    def test_invalid_20_raises(self):
        """座標系20は範囲外でValueError"""
        with self.assertRaises(ValueError):
            get_epsg(20)


if __name__ == "__main__":
    unittest.main()
