"""レイヤ分け＋GeoPackage書き出し

分類コード上位2桁×ジオメトリ型でレイヤを分割し、
QgsVectorFileWriterでGeoPackageに書き出す。
（例: "建物_面", "建物_線", "道路_面", "道路_線"）
"""
