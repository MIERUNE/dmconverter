"""CRS決定

ヘッダ/図郭レコードから座標参照系（平面直角座標系）を判定し、
対応するEPSGコードを返す。
"""

from __future__ import annotations


def get_epsg(coordinate_system: int) -> int:
    """座標系番号(1-19)からEPSGコード(JGD2011)を返す。

    平面直角座標系 1-19 → EPSG:6669-6687
    """
    if not 1 <= coordinate_system <= 19:
        raise ValueError(
            f"座標系番号が範囲外です: {coordinate_system}（1-19）"
        )
    return 6668 + coordinate_system
