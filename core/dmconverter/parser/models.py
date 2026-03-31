"""パーサーのデータ構造

分類済みレコードを解釈した結果を表すデータ構造を定義する。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Coordinate:
    """座標値（生の整数値、単位は座標単位に依存）"""

    x: int
    y: int
    z: int = 0


@dataclass(frozen=True)
class ParsedElement:
    """解析済み要素"""

    element_type: str  # "E1"-"E8"
    dm_code: str  # 4桁分類コード
    hierarchy: int  # 階層レベル
    zukei_kubun: int  # 図形区分
    data_kubun: int  # データ区分（2=2D, 3=3D）
    teni: int  # 転位区分
    kandan: int  # 間断区分
    coordinates: tuple[Coordinate, ...]  # 座標列


@dataclass(frozen=True)
class ParsedGroup:
    """解析済みグループ（H行 + 配下の要素）"""

    dm_code: str  # H行の分類コード
    elements: tuple[ParsedElement, ...]


@dataclass(frozen=True)
class MeshInfo:
    """図郭情報"""

    coordinate_system: int  # 座標系番号（1-19）
    map_name: str  # 図名
    scale: int  # 縮尺分母


@dataclass(frozen=True)
class ParsedDM:
    """解析済みDMデータ（parserの最終出力）"""

    mesh_info: MeshInfo
    groups: tuple[ParsedGroup, ...]
