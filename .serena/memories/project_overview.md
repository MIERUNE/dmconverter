# DMConverter Project Overview

## Purpose
DMファイル（数値地形図データファイル）をパースし、QGISベクタレイヤに変換するPythonモジュール。
公共測量標準図式で定義される日本の測量データをQGISエコシステムで活用可能にする。

## Core Capabilities
1. **DMファイルパース**: FORTRAN形式の固定長80バイトレコードを解析
2. **座標系変換**: 日本の平面直角座標系（第1系〜第19系）をJGD2011/JGD2000測地系に対応
3. **ジオメトリ生成**: 点・線・面・円・円弧をQGISジオメトリに変換
4. **ベクタレイヤ出力**: メモリレイヤまたはGeoPackage形式

## Tech Stack
- **Language**: Python 3.9+
- **GIS Library**: PyQGIS (QGIS 3.28+)
- **Output Format**: GeoPackage (SQLite)
- **Package Manager**: uv
- **Linter/Formatter**: ruff

## Architecture
```
Parser Layer → Converter Layer → Generator Layer
(純粋関数)      (座標変換)        (QGIS API)
```

- 関数型アーキテクチャ + レイヤード構造
- dataclass(frozen=True)によるイミュータブルデータ構造
- 副作用は最外層のみに局所化

## Key Modules
- `dmconverter/dm_parser/api.py` - 公開API関数
- `dmconverter/dm_parser/models.py` - データ構造定義
- `dmconverter/dm_parser/file_parser.py` - ファイルパース統合
- `dmconverter/dm_parser/layer_generator.py` - QGISレイヤ生成
