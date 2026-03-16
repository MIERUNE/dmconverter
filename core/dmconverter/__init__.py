"""DM変換コアモジュール

DMファイル（84バイト固定長レコード）をGeoPackageに変換するパイプライン。
処理フロー:
    reader → classifier → parser → geometry + crs → writer
"""

from pathlib import Path
from typing import List, Optional

