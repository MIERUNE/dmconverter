"""レコード解釈パッケージ

分離したレコードの中身（分類コード、座標値など）を意味のあるデータとして解釈する。
"""

from .models import (  # noqa: F401
    Coordinate,
    MeshInfo,
    ParsedDM,
    ParsedElement,
    ParsedGroup,
)
from .parser import parse  # noqa: F401
