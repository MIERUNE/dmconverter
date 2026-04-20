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
class AnnotationInfo:
    """E7注記の表示情報（後続の注記レコードから取得）"""

    orientation: int  # 縦横区分 (0=横書き, 1=縦書き)
    angle: int  # 文字列の方向 (度)
    size: int  # 字大 (0.1mm単位)
    spacing: int  # 字隔 (0.1mm単位)
    line_weight: int  # 線号
    text: str  # 注記データ


@dataclass(frozen=True)
class AttributeInfo:
    """E8属性データ（後続の属性レコードから取得）"""

    data: str  # 属性データ（生の文字列）


@dataclass(frozen=True)
class ParsedElement:
    """解析済み要素"""

    element_type: str  # "E1"-"E8"
    dm_code: str  # 4桁分類コード
    chiiki_bunrui: int  # 地域分類
    jouhou_bunrui: int  # 情報分類
    element_id: int  # 要素識別番号
    hierarchy: int  # 階層レベル
    zukei_kubun: int  # 図形区分
    data_kubun: int  # データ区分（2=2D, 3=3D）
    seido_kubun: int  # 精度区分
    chuki_kubun: int  # 注記区分
    teni: int  # 転位区分
    kandan: int  # 間断区分
    coordinates: tuple[Coordinate, ...]  # 座標列
    attribute_value: int = 0  # 属性数値（標高値等）
    zokusei_kubun: int = 0  # 属性区分
    acquired_date: str | None = None  # 取得年月（YYYY/MM or None）
    updated_date: str | None = None  # 更新取得年月（YYYY/MM or None）
    deleted_date: str | None = None  # 消去年月（YYYY/MM or None）
    annotation: AnnotationInfo | None = None  # E7のみ
    attribute: AttributeInfo | None = None  # E8のみ


@dataclass(frozen=True)
class ParsedGroup:
    """解析済みグループ（H行 + 配下の要素）"""

    dm_code: str  # H行の分類コード
    elements: tuple[ParsedElement, ...]


@dataclass(frozen=True)
class MeshInfo:
    """図郭情報（図郭レコード(a)から取得）"""

    coordinate_system: int  # 座標系番号（1-19）
    map_name: str  # 図名
    scale: int  # 縮尺分母


@dataclass(frozen=True)
class MapSheetInfo:
    """図郭情報（図郭レコード(b)から取得）"""

    origin_x: int  # 左下図郭座標 X (メートル)
    origin_y: int  # 左下図郭座標 Y (メートル)
    upper_x: int  # 右上図郭座標 X (メートル)
    upper_y: int  # 右上図郭座標 Y (メートル)
    coord_unit: int  # 座標値の単位 (1=mm, 10=cm, 999=m)


@dataclass(frozen=True)
class ParsedDM:
    """解析済みDMデータ（parserの最終出力）"""

    mesh_info: MeshInfo
    map_sheet: MapSheetInfo
    groups: tuple[ParsedGroup, ...]
