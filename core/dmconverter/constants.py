"""定数定義

レコードタイプ、分類コード表（上位2桁→レイヤ名）、
CRSマッピング（座標系番号→EPSG）。
"""

RECORD_LENGTH = 84

# 座標フィールド
COORD_FIELD_WIDTH = 7
COORDS_PER_LINE_2D = 6
COORDS_PER_LINE_3D = 4

# Mレコード（図郭レコード）関連
MESH_BASE_ROWS = 3  # (a)(b)(c) の固定3行
MESH_HISTORY_SET_ROWS = 3  # (d)(e)(f) 1セットあたり3行
REVISION_COUNT_POSITION = 65  # 図郭レコード(a)の修正回数の位置（0始点、I2）
