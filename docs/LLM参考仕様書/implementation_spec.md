# DM→GeoPackage変換ツール 実装仕様書

**バージョン**: 1.0  
**作成日**: 2026-02-04  
**対象**: LLMによるAI開発

---

## 目次

1. [プロジェクト概要](#1-プロジェクト概要)
2. [DMフォーマット詳細仕様](#2-dmフォーマット詳細仕様)
3. [GeoPackage出力仕様](#3-geopackage出力仕様)
4. [データ変換ロジック](#4-データ変換ロジック)
5. [実装ガイドライン](#5-実装ガイドライン)
6. [テスト要件](#6-テスト要件)
7. [既知の制約事項](#7-既知の制約事項)

---

## 1. プロジェクト概要

### 1.1 目的

国土地理院が定義するDM（デジタルマッピング）形式の地理空間データを、OGC標準のGeoPackage形式に変換するPythonライブラリとQGISプラグインを開発する。

### 1.2 アーキテクチャ

```
dm_loader/
├── dm_parser/              # コアパーサー（QGIS非依存）
│   ├── __init__.py
│   ├── parser.py           # DMファイル読み込み
│   ├── records.py          # レコードタイプ別パース
│   ├── coordinate.py       # 座標系変換
│   ├── layer_codes.py      # 分類コードマッピング
│   ├── geometry.py         # ジオメトリ構造化
│   ├── gpkg_writer.py      # GeoPackage書き込み
│   └── utils.py            # ユーティリティ
├── qgis_plugin/            # QGIS Processingプラグイン
│   ├── __init__.py
│   ├── dm_loader_provider.py     # Processing Provider
│   ├── dm_loader_algorithm.py    # Processing Algorithm
│   ├── metadata.txt              # プラグインメタデータ
│   └── icon.png                  # プラグインアイコン
└── tests/                  # テストコード
```

### 1.3 開発フロー

1. **コアパーサー**: DMファイル → Python辞書リスト
2. **GeoPackageライター**: Python辞書リスト → .gpkgファイル
3. **QGIS Processingプラグイン**: Processing Toolboxから実行、GeoPackageを自動レイヤー追加

---

## 2. DMフォーマット詳細仕様

### 2.1 基本構造

DMファイルは**固定長84バイトのレコード**がテキスト形式で連続するファイルフォーマット。

#### ファイル構造
```
[図郭レコード M]
  [要素グループヘッダ G]
    [要素データ E1]
      [実データ R1-1]
      [実データ R1-2]
      ...
    [要素データ E2]
      [実データ R2-1]
      ...
  [要素グループヘッダ G]
    ...
[図郭レコード M] (次の図郭)
  ...
```

### 2.2 レコードタイプ

| レコードタイプ | 識別子 | 説明 |
|---|---|---|
| 図郭レコード | M | ファイルのメタ情報、座標系情報 |
| 要素グループヘッダ | G | 地物グループの開始 |
| 要素レコード | E | 個別地物の属性情報 |
| 実データレコード | R | 座標データ本体 |
| 注記レコード | J | テキスト注記 |

### 2.3 レコード構造詳細

#### 2.3.1 図郭レコード（M）

**バイト位置とフィールド定義**:

| バイト位置 | 長さ | 型 | フィールド名 | 説明 |
|---|---|---|---|---|
| 1-2 | 2 | A | レコードタイプ | "M " (Mの後にスペース) |
| 3-10 | 8 | A | 図郭識別番号 | 座標系番号(2桁)+図郭名(6桁) |
| 11-14 | 4 | I | バージョン | DMフォーマットバージョン |
| 15-22 | 8 | A | 測地成果 | "2000" または "2011" |
| 23-30 | 8 | I | 左下X座標 | 図郭左下の平面直角座標X (mm単位) |
| 31-38 | 8 | I | 左下Y座標 | 図郭左下の平面直角座標Y (mm単位) |
| 39-46 | 8 | I | 右上X座標 | 図郭右上の平面直角座標X (mm単位) |
| 47-54 | 8 | I | 右上Y座標 | 図郭右上の平面直角座標Y (mm単位) |
| 55-84 | 30 | A | 予備 | 空白 |

**重要事項**:
- 図郭識別番号の先頭2桁が座標系番号（01-19）
- 座標値はミリメートル単位 → メートル単位に変換が必要（÷1000）

**実装例**:
```python
def parse_m_record(line: bytes) -> dict:
    """図郭レコードをパース"""
    record = {
        'record_type': line[0:2].decode('ascii').strip(),
        'zukaku_id': line[2:10].decode('ascii').strip(),
        'version': int(line[10:14]),
        'datum': line[14:22].decode('ascii').strip(),
        'bbox': {
            'min_x': int(line[22:30]) / 1000.0,  # mm → m
            'min_y': int(line[30:38]) / 1000.0,
            'max_x': int(line[38:46]) / 1000.0,
            'max_y': int(line[46:54]) / 1000.0
        }
    }
    # 座標系番号を抽出
    record['crs_code'] = int(record['zukaku_id'][:2])
    return record
```

#### 2.3.2 要素グループヘッダレコード（G）

| バイト位置 | 長さ | 型 | フィールド名 | 説明 |
|---|---|---|---|---|
| 1-2 | 2 | A | レコードタイプ | "G " |
| 3-6 | 4 | A | 分類コード | 4桁の地物分類 (例: "1100", "2100") |
| 7-10 | 4 | I | グループ内要素数 | このグループに含まれる要素数 |
| 11-84 | 74 | A | 予備 | 空白 |

**分類コード体系**:
- 1xxx: 境界
- 2xxx: 道路・道路施設
- 3xxx: 建物
- 4xxx: 鉄道・水路
- 5xxx: 小物体
- 6xxx: 土地利用
- 7xxx: 地形
- 8xxx: 注記・付属情報

**実装例**:
```python
def parse_g_record(line: bytes) -> dict:
    """要素グループヘッダをパース"""
    return {
        'record_type': line[0:2].decode('ascii').strip(),
        'bunrui_code': line[2:6].decode('ascii').strip(),
        'element_count': int(line[6:10])
    }
```

#### 2.3.3 要素レコード（E）

| バイト位置 | 長さ | 型 | フィールド名 | 説明 |
|---|---|---|---|---|
| 1-2 | 2 | A | レコードタイプ | "E1"-"E8" (図形タイプ) |
| 3-6 | 4 | A | 分類コード | 親グループと同じ |
| 7-10 | 4 | I | 要素識別番号 | グループ内の通し番号 |
| 11-12 | 2 | A | 図形区分 | "00"-"99" |
| 13-16 | 4 | I | 実データ数 | このE素に属するRレコード数 |
| 17-18 | 2 | I | 精度区分 | 測量精度 |
| 19-26 | 8 | I | 代表点X | 地物の代表座標X (mm) |
| 27-34 | 8 | I | 代表点Y | 地物の代表座標Y (mm) |
| 35-42 | 8 | I | 代表点Z | 標高 (mm、未入力は0) |
| 43-84 | 42 | A | 属性データ | 地物固有の属性 |

**図形区分（Eレコードタイプ）**:

| タイプ | 説明 | ジオメトリ |
|---|---|---|
| E1 | 点 | Point |
| E2 | 線 | LineString |
| E3 | 面 | Polygon |
| E4 | 方向 | Point with rotation |
| E5 | 円 | Circle (Point + radius) |
| E6 | 円弧 | Arc |
| E7 | 楕円 | Ellipse |
| E8 | 多角形（穴あり） | Polygon with holes |

**実装例**:
```python
def parse_e_record(line: bytes) -> dict:
    """要素レコードをパース"""
    record_type = line[0:2].decode('ascii').strip()
    return {
        'record_type': record_type,
        'geometry_type': {
            'E1': 'Point',
            'E2': 'LineString',
            'E3': 'Polygon',
            'E4': 'Point',  # 方向付き
            'E5': 'Point',  # 円
            'E6': 'LineString',  # 円弧
            'E7': 'Polygon',  # 楕円
            'E8': 'Polygon'  # 穴あき多角形
        }.get(record_type, 'Unknown'),
        'bunrui_code': line[2:6].decode('ascii').strip(),
        'element_id': int(line[6:10]),
        'zukei_kubun': line[10:12].decode('ascii').strip(),
        'data_count': int(line[12:16]),
        'seido_kubun': int(line[16:18]),
        'repr_point': {
            'x': int(line[18:26]) / 1000.0,
            'y': int(line[26:34]) / 1000.0,
            'z': int(line[34:42]) / 1000.0 if line[34:42].strip() else None
        },
        'attributes': line[42:84].decode('shift_jis', errors='ignore').strip()
    }
```

#### 2.3.4 実データレコード（R）

| バイト位置 | 長さ | 型 | フィールド名 | 説明 |
|---|---|---|---|---|
| 1-2 | 2 | A | レコードタイプ | "R " |
| 3-10 | 8 | I | X座標 | 平面直角座標X (mm) |
| 11-18 | 8 | I | Y座標 | 平面直角座標Y (mm) |
| 19-26 | 8 | I | Z座標 | 標高 (mm、未入力は0) |
| 27-84 | 58 | A | 予備 | 空白 |

**実装例**:
```python
def parse_r_record(line: bytes) -> dict:
    """実データレコードをパース"""
    return {
        'record_type': line[0:2].decode('ascii').strip(),
        'x': int(line[2:10]) / 1000.0,  # mm → m
        'y': int(line[10:18]) / 1000.0,
        'z': int(line[18:26]) / 1000.0 if line[18:26].strip() else None
    }
```

### 2.4 文字エンコーディング

**エンコーディングルール**:
- **半角文字**: ASCII
- **全角文字**: Shift-JIS

**実装時の注意**:
```python
# ファイル読み込み
with open(dm_file, 'rb') as f:
    for line in f:
        # 固定長84バイトで処理
        if len(line) < 84:
            continue
        
        # ASCIIフィールド（レコードタイプ、コード類）
        record_type = line[0:2].decode('ascii')
        
        # Shift-JISフィールド（属性データ、注記）
        attributes = line[42:84].decode('shift_jis', errors='replace')
```

### 2.5 座標系

**平面直角座標系（19系統）**:

| 系番号 | 適用地域 | EPSG コード |
|---|---|---|
| 01 | 長崎県（一部） | EPSG:6669 |
| 02 | 福岡県・佐賀県等 | EPSG:6670 |
| 03 | 山口県・島根県等 | EPSG:6671 |
| 04 | 香川県・徳島県等 | EPSG:6672 |
| 05 | 兵庫県・大阪府等 | EPSG:6673 |
| 06 | 京都府・福井県等 | EPSG:6674 |
| 07 | 石川県・富山県等 | EPSG:6675 |
| 08 | 新潟県・福島県等 | EPSG:6676 |
| 09 | 東京都・神奈川県等 | EPSG:6677 |
| 10 | 青森県・秋田県等 | EPSG:6678 |
| 11 | 北海道（小樽等） | EPSG:6679 |
| 12 | 北海道（北見等） | EPSG:6680 |
| 13 | 北海道（釧路等） | EPSG:6681 |
| 14 | 東京都（離島） | EPSG:6682 |
| 15 | 沖縄県（一部） | EPSG:6683 |
| 16 | 沖縄県（一部） | EPSG:6684 |
| 17 | 沖縄県（一部） | EPSG:6685 |
| 18 | 沖縄県（本島等） | EPSG:6686 |
| 19 | 沖縄県（一部） | EPSG:6687 |

**座標変換実装**:
```python
from pyproj import CRS, Transformer

def get_crs_from_code(crs_code: int) -> CRS:
    """座標系番号からCRSオブジェクトを取得"""
    epsg_code = 6668 + crs_code  # 6669-6687
    return CRS.from_epsg(epsg_code)

def transform_coordinates(coords: list, source_crs: CRS, target_crs: CRS) -> list:
    """座標変換"""
    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    return [transformer.transform(x, y) for x, y in coords]
```

### 2.6 分類コード体系

**主要分類（@DmLayerNameList.txtより）**:

#### 境界（1xxx）
- 1100: 境界
- 1101: 都府県界
- 1102: 北海道の支庁界
- 1103: 郡市・東京都の区界
- 1104: 町村・指定都市の区界

#### 道路（2xxx）
- 2100: 道路
- 2101: 道路縁（街区線）
- 2102: 軽車道
- 2200: 道路施設
- 2203: 道路橋

#### 建物（3xxx）
- 3000: 建物
- 3001: 普通建物
- 3002: 堅ろう建物

#### 鉄道・水路（4xxx）
- 4100: 鉄道
- 4101: JR線
- 4200: 水路
- 4201: 河川

#### 土地利用（6xxx）
- 6311: 田
- 6312: 畑
- 6331: 森林

---

## 3. GeoPackage出力仕様

### 3.1 GeoPackageフォーマット概要

- **ベース**: SQLite3データベース
- **標準**: OGC GeoPackage 1.2+
- **拡張子**: `.gpkg`
- **特徴**: 複数レイヤーを1ファイルに格納可能

### 3.2 テーブル構造

#### 3.2.1 レイヤーテーブル

各分類コードごとに1つのテーブルを作成:

**テーブル名規則**: `layer_{分類コード}` (例: `layer_1100`, `layer_2100`)

**カラム定義**:

| カラム名 | 型 | 説明 |
|---|---|---|
| fid | INTEGER PRIMARY KEY | フィーチャーID（自動採番） |
| geom | GEOMETRY | ジオメトリ（Point/LineString/Polygon） |
| bunrui_code | TEXT | 分類コード（4桁） |
| bunrui_name | TEXT | 分類名称（日本語） |
| element_id | INTEGER | 要素識別番号 |
| zukei_kubun | TEXT | 図形区分 |
| seido_kubun | INTEGER | 精度区分 |
| repr_x | REAL | 代表点X座標 |
| repr_y | REAL | 代表点Y座標 |
| repr_z | REAL | 代表点Z座標（標高） |
| attributes | TEXT | その他属性（JSON形式） |

#### 3.2.2 メタデータテーブル

GeoPackage標準の`gpkg_contents`, `gpkg_spatial_ref_sys`等は自動生成。

### 3.3 ジオメトリ型の対応

| DMタイプ | GeoPackageジオメトリ | 備考 |
|---|---|---|
| E1 (点) | Point | |
| E2 (線) | LineString | |
| E3 (面) | Polygon | 外周のみ |
| E4 (方向) | Point | rotation属性を追加カラムで保持 |
| E5 (円) | Polygon | 円を多角形近似（36頂点） |
| E6 (円弧) | LineString | 円弧を線分近似 |
| E7 (楕円) | Polygon | 楕円を多角形近似 |
| E8 (多角形) | Polygon | 穴あき多角形対応 |

### 3.4 CRS設定

**GeoPackage内のCRS定義**:

```sql
INSERT INTO gpkg_spatial_ref_sys (
    srs_name, srs_id, organization, 
    organization_coordsys_id, definition
) VALUES (
    'JGD2011 / Japan Plane Rectangular CS IX',
    6677,
    'EPSG',
    6677,
    'PROJ.4定義文字列...'
);
```

**fiona/GDALでのCRS設定**:
```python
import fiona
from fiona.crs import from_epsg

schema = {
    'geometry': 'LineString',
    'properties': {
        'bunrui_code': 'str',
        'bunrui_name': 'str',
        # ...
    }
}

crs = from_epsg(6677)  # 平面直角座標系9系

with fiona.open(
    'output.gpkg',
    'w',
    driver='GPKG',
    layer='layer_1100',
    schema=schema,
    crs=crs
) as dst:
    # データ書き込み
    pass
```

### 3.5 複数レイヤーの格納

**レイヤー追加方法**:
```python
# 1つ目のレイヤー
with fiona.open('output.gpkg', 'w', driver='GPKG', 
                layer='layer_1100', schema=schema1, crs=crs) as dst1:
    dst1.write(feature1)

# 2つ目以降のレイヤー（'a'モード）
with fiona.open('output.gpkg', 'a', driver='GPKG',
                layer='layer_2100', schema=schema2, crs=crs) as dst2:
    dst2.write(feature2)
```

---

## 4. データ変換ロジック

### 4.1 全体フロー

```
[DMファイル読み込み]
      ↓
[レコード分離・パース]
      ↓
[地物ごとにグループ化]
      ↓
[ジオメトリ構築]
      ↓
[座標変換]
      ↓
[GeoPackage書き込み]
```

### 4.2 パーサー実装

#### 4.2.1 DMファイル読み込み

```python
def read_dm_file(filepath: str) -> list:
    """
    DMファイルを読み込み、レコードリストを返す
    
    Args:
        filepath: DMファイルパス
        
    Returns:
        レコードの辞書リスト
    """
    records = []
    
    with open(filepath, 'rb') as f:
        for line_num, line in enumerate(f, 1):
            # 固定長84バイトチェック
            if len(line) < 84:
                continue
            
            # EOF (0x1A) チェック
            if line[0] == 0x1A:
                break
            
            # レコードタイプ判定
            record_type = line[0:2].decode('ascii', errors='ignore').strip()
            
            try:
                if record_type == 'M':
                    records.append(parse_m_record(line))
                elif record_type == 'G':
                    records.append(parse_g_record(line))
                elif record_type.startswith('E'):
                    records.append(parse_e_record(line))
                elif record_type == 'R':
                    records.append(parse_r_record(line))
                else:
                    # 未知のレコードタイプ
                    logging.warning(f"Unknown record type: {record_type} at line {line_num}")
            except Exception as e:
                logging.error(f"Error parsing line {line_num}: {e}")
                continue
    
    return records
```

#### 4.2.2 地物グループ化

```python
def group_by_features(records: list) -> dict:
    """
    レコードリストを地物ごとにグループ化
    
    Returns:
        {
            'zukaku': {...},  # 図郭情報
            'layers': {
                '1100': [feature1, feature2, ...],
                '2100': [feature3, ...],
            }
        }
    """
    result = {
        'zukaku': None,
        'layers': {}
    }
    
    current_group = None
    current_element = None
    current_coords = []
    
    for record in records:
        rtype = record['record_type']
        
        if rtype == 'M':
            result['zukaku'] = record
        
        elif rtype == 'G':
            current_group = record['bunrui_code']
            if current_group not in result['layers']:
                result['layers'][current_group] = []
        
        elif rtype.startswith('E'):
            # 前の要素を保存
            if current_element is not None:
                current_element['coordinates'] = current_coords
                result['layers'][current_group].append(current_element)
            
            # 新しい要素開始
            current_element = record
            current_coords = []
        
        elif rtype == 'R':
            if current_element is not None:
                current_coords.append([record['x'], record['y'], record.get('z')])
    
    # 最後の要素を保存
    if current_element is not None:
        current_element['coordinates'] = current_coords
        result['layers'][current_group].append(current_element)
    
    return result
```

### 4.3 ジオメトリ構築

#### 4.3.1 点（E1）

```python
def build_point_geometry(element: dict) -> dict:
    """点ジオメトリ構築"""
    coords = element.get('coordinates', [])
    if len(coords) > 0:
        return {
            'type': 'Point',
            'coordinates': coords[0][:2]  # [x, y]
        }
    # 座標がない場合は代表点を使用
    return {
        'type': 'Point',
        'coordinates': [
            element['repr_point']['x'],
            element['repr_point']['y']
        ]
    }
```

#### 4.3.2 線（E2）

```python
def build_linestring_geometry(element: dict) -> dict:
    """線ジオメトリ構築"""
    coords = element.get('coordinates', [])
    return {
        'type': 'LineString',
        'coordinates': [c[:2] for c in coords]  # [[x1,y1], [x2,y2], ...]
    }
```

#### 4.3.3 面（E3, E8）

```python
def build_polygon_geometry(element: dict) -> dict:
    """面ジオメトリ構築"""
    coords = element.get('coordinates', [])
    
    # 外周を閉じる（始点と終点を一致させる）
    if len(coords) > 0 and coords[0] != coords[-1]:
        coords.append(coords[0])
    
    ring = [c[:2] for c in coords]
    
    return {
        'type': 'Polygon',
        'coordinates': [ring]  # 外周のみ（穴は別途処理）
    }
```

#### 4.3.4 円（E5）→多角形近似

```python
import math

def build_circle_geometry(element: dict, num_points: int = 36) -> dict:
    """円を多角形近似"""
    center_x = element['repr_point']['x']
    center_y = element['repr_point']['y']
    
    # 半径は属性データまたは最初の座標点から計算
    coords = element.get('coordinates', [])
    if len(coords) > 0:
        dx = coords[0][0] - center_x
        dy = coords[0][1] - center_y
        radius = math.sqrt(dx*dx + dy*dy)
    else:
        radius = 10.0  # デフォルト半径
    
    # 円周上の点を生成
    points = []
    for i in range(num_points):
        angle = 2 * math.pi * i / num_points
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        points.append([x, y])
    
    points.append(points[0])  # 閉じる
    
    return {
        'type': 'Polygon',
        'coordinates': [points]
    }
```

### 4.4 座標変換

```python
from pyproj import CRS, Transformer

def transform_geometry(geometry: dict, source_epsg: int, target_epsg: int = 4326) -> dict:
    """
    ジオメトリの座標系を変換
    
    Args:
        geometry: GeoJSON形式のジオメトリ
        source_epsg: 元のEPSGコード
        target_epsg: 変換先のEPSGコード (デフォルトWGS84)
    
    Returns:
        変換後のジオメトリ
    """
    transformer = Transformer.from_crs(
        CRS.from_epsg(source_epsg),
        CRS.from_epsg(target_epsg),
        always_xy=True
    )
    
    geom_type = geometry['type']
    coords = geometry['coordinates']
    
    if geom_type == 'Point':
        x, y = transformer.transform(coords[0], coords[1])
        return {'type': 'Point', 'coordinates': [x, y]}
    
    elif geom_type == 'LineString':
        new_coords = [transformer.transform(x, y) for x, y in coords]
        return {'type': 'LineString', 'coordinates': new_coords}
    
    elif geom_type == 'Polygon':
        new_rings = []
        for ring in coords:
            new_ring = [transformer.transform(x, y) for x, y in ring]
            new_rings.append(new_ring)
        return {'type': 'Polygon', 'coordinates': new_rings}
    
    return geometry
```

### 4.5 GeoPackage書き込み

```python
import fiona
from fiona.crs import from_epsg

def write_to_geopackage(
    features_by_layer: dict,
    output_path: str,
    crs_epsg: int,
    layer_names: dict
):
    """
    GeoPackageファイルに書き込み
    
    Args:
        features_by_layer: レイヤーコード別の地物リスト
        output_path: 出力.gpkgファイルパス
        crs_epsg: EPSGコード
        layer_names: 分類コード→レイヤー名のマッピング
    """
    crs = from_epsg(crs_epsg)
    first_layer = True
    
    for bunrui_code, features in features_by_layer.items():
        if len(features) == 0:
            continue
        
        # ジオメトリタイプを判定
        geom_type = determine_geometry_type(features)
        
        # スキーマ定義
        schema = {
            'geometry': geom_type,
            'properties': {
                'bunrui_code': 'str',
                'bunrui_name': 'str',
                'element_id': 'int',
                'zukei_kubun': 'str',
                'seido_kubun': 'int',
                'repr_x': 'float',
                'repr_y': 'float',
                'repr_z': 'float',
                'attributes': 'str'
            }
        }
        
        layer_name = f"layer_{bunrui_code}"
        mode = 'w' if first_layer else 'a'
        
        with fiona.open(
            output_path,
            mode,
            driver='GPKG',
            layer=layer_name,
            schema=schema,
            crs=crs
        ) as dst:
            for feature in features:
                # GeoJSON Feature形式
                fiona_feature = {
                    'geometry': feature['geometry'],
                    'properties': {
                        'bunrui_code': feature['bunrui_code'],
                        'bunrui_name': layer_names.get(feature['bunrui_code'], ''),
                        'element_id': feature['element_id'],
                        'zukei_kubun': feature.get('zukei_kubun', ''),
                        'seido_kubun': feature.get('seido_kubun', 0),
                        'repr_x': feature['repr_point']['x'],
                        'repr_y': feature['repr_point']['y'],
                        'repr_z': feature['repr_point'].get('z'),
                        'attributes': feature.get('attributes', '')
                    }
                }
                dst.write(fiona_feature)
        
        first_layer = False

def determine_geometry_type(features: list) -> str:
    """フィーチャーリストから主要なジオメトリタイプを判定"""
    types = [f['geometry']['type'] for f in features]
    # 最頻値を返す
    return max(set(types), key=types.count)
```

### 4.6 エラーハンドリング

```python
class DMParseError(Exception):
    """DMパースエラー"""
    pass

class GeometryBuildError(Exception):
    """ジオメトリ構築エラー"""
    pass

def safe_parse_record(line: bytes, line_num: int) -> dict:
    """安全なレコードパース"""
    try:
        record_type = line[0:2].decode('ascii').strip()
        
        if record_type == 'M':
            return parse_m_record(line)
        elif record_type == 'G':
            return parse_g_record(line)
        # ...
        
    except UnicodeDecodeError as e:
        raise DMParseError(f"Line {line_num}: Encoding error - {e}")
    except ValueError as e:
        raise DMParseError(f"Line {line_num}: Value error - {e}")
    except Exception as e:
        raise DMParseError(f"Line {line_num}: Unexpected error - {e}")
```

---

## 5. 実装ガイドライン

### 5.1 推奨ライブラリ

| ライブラリ | バージョン | 用途 |
|---|---|---|
| Python | 3.8+ | ベース言語 |
| pyproj | 3.x | 座標系変換 |
| fiona | 1.9+ | GeoPackage書き込み |
| shapely | 2.x | ジオメトリ操作（オプション） |
| pytest | 7.x | テスト |
| black | 23.x | コードフォーマット |
| mypy | 1.x | 型チェック |

### 5.2 コーディング規約

#### 5.2.1 型ヒント

**必須**: すべての関数に型ヒントを付与

```python
from typing import List, Dict, Optional, Tuple

def parse_dm_file(filepath: str) -> List[Dict]:
    """DMファイルをパース"""
    pass

def transform_coordinate(
    x: float, 
    y: float, 
    source_epsg: int, 
    target_epsg: int
) -> Tuple[float, float]:
    """座標変換"""
    pass
```

#### 5.2.2 Docstring

**Google Style**を使用:

```python
def build_polygon_geometry(element: dict, close_ring: bool = True) -> dict:
    """
    面ジオメトリを構築する
    
    Args:
        element: 要素レコードの辞書
        close_ring: True の場合、始点と終点を一致させる
    
    Returns:
        GeoJSON形式のPolygonジオメトリ
        
    Raises:
        GeometryBuildError: 座標データが不正な場合
        
    Examples:
        >>> element = {'coordinates': [[0,0], [1,0], [1,1], [0,1]]}
        >>> geom = build_polygon_geometry(element)
        >>> geom['type']
        'Polygon'
    """
    pass
```

#### 5.2.3 ロギング

```python
import logging

# モジュールレベルでロガー設定
logger = logging.getLogger(__name__)

def parse_dm_file(filepath: str) -> List[Dict]:
    logger.info(f"Parsing DM file: {filepath}")
    
    try:
        # ...処理...
        logger.info(f"Successfully parsed {len(records)} records")
        return records
    except Exception as e:
        logger.error(f"Failed to parse DM file: {e}", exc_info=True)
        raise
```

### 5.3 プロジェクト構造

```
dm_loader/
├── dm_parser/
│   ├── __init__.py
│   ├── parser.py           # メインパーサー
│   ├── records.py          # レコード型別パーサー
│   ├── coordinate.py       # 座標変換
│   ├── geometry.py         # ジオメトリ構築
│   ├── layer_codes.py      # 分類コードマッピング
│   ├── gpkg_writer.py      # GeoPackage書き込み
│   └── utils.py            # ユーティリティ
├── qgis_plugin/
│   ├── __init__.py         # プラグイン初期化
│   ├── dm_loader_provider.py    # Processing Provider
│   ├── dm_loader_algorithm.py   # Processing Algorithm
│   ├── metadata.txt             # プラグインメタデータ
│   └── icon.png                 # プラグインアイコン
├── tests/
│   ├── test_parser.py
│   ├── test_records.py
│   ├── test_coordinate.py
│   ├── test_geometry.py
│   ├── test_gpkg_writer.py
│   ├── test_processing.py       # Processing実行テスト
│   └── fixtures/                # テスト用DMファイル
├── docs/
│   ├── implementation_spec.md   # 本ドキュメント
│   └── dm_format_analysis.md
├── data/
│   └── @DmLayerNameList.txt
├── requirements.txt
├── setup.py
└── README.md
```

### 5.4 requirements.txt

```txt
# コアライブラリ
pyproj>=3.4.0
fiona>=1.9.0
shapely>=2.0.0

# 開発ツール
pytest>=7.4.0
pytest-cov>=4.1.0
black>=23.7.0
flake8>=6.1.0
mypy>=1.5.0

# ドキュメント
sphinx>=7.1.0
sphinx-rtd-theme>=1.3.0
```

---

## 6. QGIS Processingプラグイン実装詳細

### 6.1 Processingプラグインの構造

QGIS Processingプラグインは、**Processing Toolbox**から利用できるアルゴリズム形式のプラグイン。ダイアログ形式と異なり、バッチ処理やモデルデザイナーからの利用が可能。

### 6.2 metadata.txt

```ini
[general]
name=DM Loader
qgisMinimumVersion=3.0
description=Load Digital Mapping (DM) format files and convert to GeoPackage
version=1.0.0
author=Your Name
email=your.email@example.com
about=This plugin loads Japanese Digital Mapping (DM) format files and converts them to GeoPackage format with automatic layer loading.
homepage=https://github.com/yourname/dm_loader
tracker=https://github.com/yourname/dm_loader/issues
repository=https://github.com/yourname/dm_loader
category=Vector
tags=dm,digital mapping,geopackage,japan,converter
icon=icon.png
experimental=False
deprecated=False
```

### 6.3 __init__.py

```python
# -*- coding: utf-8 -*-
"""
DM Loader QGIS Plugin
"""

def classFactory(iface):
    """
    Load DmLoaderPlugin class from file dm_loader_plugin
    
    Args:
        iface: QGISインターフェース
        
    Returns:
        DmLoaderPlugin instance
    """
    from .dm_loader_plugin import DmLoaderPlugin
    return DmLoaderPlugin(iface)
```

### 6.4 dm_loader_plugin.py (プラグインメイン)

```python
# -*- coding: utf-8 -*-
from qgis.core import QgsApplication
from .dm_loader_provider import DmLoaderProvider

class DmLoaderPlugin:
    """
    DM Loader QGIS Plugin
    """
    
    def __init__(self, iface):
        """
        プラグイン初期化
        
        Args:
            iface: QGISインターフェース
        """
        self.iface = iface
        self.provider = None
    
    def initProcessing(self):
        """
        Processing Providerを登録
        """
        self.provider = DmLoaderProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)
    
    def initGui(self):
        """
        GUI初期化（Processingプラグインでは特に不要）
        """
        self.initProcessing()
    
    def unload(self):
        """
        プラグインアンロード
        """
        QgsApplication.processingRegistry().removeProvider(self.provider)
```

### 6.5 dm_loader_provider.py (Processing Provider)

```python
# -*- coding: utf-8 -*-
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
import os

from .dm_loader_algorithm import DmLoaderAlgorithm

class DmLoaderProvider(QgsProcessingProvider):
    """
    DM Loader Processing Provider
    """
    
    def id(self):
        """
        Providerの一意ID
        """
        return 'dm_loader'
    
    def name(self):
        """
        Providerの表示名
        """
        return 'DM Loader'
    
    def icon(self):
        """
        Providerのアイコン
        """
        return QIcon(os.path.join(os.path.dirname(__file__), 'icon.png'))
    
    def loadAlgorithms(self):
        """
        アルゴリズムを登録
        """
        self.addAlgorithm(DmLoaderAlgorithm())
```

### 6.6 dm_loader_algorithm.py (Processing Algorithm)

```python
# -*- coding: utf-8 -*-
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterCrs,
    QgsProcessingParameterBoolean,
    QgsProcessingOutputVectorLayer,
    QgsProcessingException,
    QgsVectorLayer,
    QgsProject,
    QgsCrs
)
from qgis.PyQt.QtCore import QCoreApplication
import os
import sys

# コアパーサーをインポート
# プラグインディレクトリの親ディレクトリをパスに追加
parent_dir = os.path.dirname(os.path.dirname(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from dm_parser.parser import read_dm_file, group_by_features
from dm_parser.geometry import build_geometry
from dm_parser.gpkg_writer import write_to_geopackage
from dm_parser.layer_codes import load_layer_names
from dm_parser.coordinate import get_crs_from_code

class DmLoaderAlgorithm(QgsProcessingAlgorithm):
    """
    DMファイルをGeoPackageに変換するProcessing Algorithm
    """
    
    # パラメータ名
    INPUT_DM_FILE = 'INPUT_DM_FILE'
    OUTPUT_GPKG = 'OUTPUT_GPKG'
    TARGET_CRS = 'TARGET_CRS'
    ADD_TO_MAP = 'ADD_TO_MAP'
    
    def tr(self, string):
        """
        多言語対応用文字列変換
        """
        return QCoreApplication.translate('DmLoaderAlgorithm', string)
    
    def createInstance(self):
        """
        アルゴリズムの新しいインスタンスを作成
        """
        return DmLoaderAlgorithm()
    
    def name(self):
        """
        アルゴリズムの内部名
        """
        return 'dm_to_geopackage'
    
    def displayName(self):
        """
        アルゴリズムの表示名
        """
        return self.tr('DM to GeoPackage')
    
    def group(self):
        """
        グループ名
        """
        return self.tr('Converter')
    
    def groupId(self):
        """
        グループID
        """
        return 'converter'
    
    def shortHelpString(self):
        """
        アルゴリズムの簡単な説明
        """
        return self.tr(
            'Load Japanese Digital Mapping (DM) format files and '
            'convert them to GeoPackage format.\n\n'
            'The DM format is a fixed-length 84-byte record format '
            'used in Japan for public surveying. This algorithm parses '
            'DM files and outputs a GeoPackage with multiple layers '
            'based on classification codes.'
        )
    
    def initAlgorithm(self, config=None):
        """
        パラメータ定義
        """
        # 入力DMファイル
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_DM_FILE,
                self.tr('Input DM File'),
                behavior=QgsProcessingParameterFile.File,
                fileFilter=self.tr('DM Files (*.dm *.DM);;All Files (*.*)')
            )
        )
        
        # 出力GeoPackageファイル
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_GPKG,
                self.tr('Output GeoPackage'),
                fileFilter=self.tr('GeoPackage (*.gpkg)')
            )
        )
        
        # ターゲットCRS（オプション、デフォルトはDMファイルのCRSを使用）
        self.addParameter(
            QgsProcessingParameterCrs(
                self.TARGET_CRS,
                self.tr('Target CRS (optional)'),
                optional=True
            )
        )
        
        # マップに追加
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.ADD_TO_MAP,
                self.tr('Add layers to map'),
                defaultValue=True
            )
        )
    
    def processAlgorithm(self, parameters, context, feedback):
        """
        アルゴリズムの実行
        
        Args:
            parameters: パラメータ辞書
            context: Processingコンテキスト
            feedback: フィードバックオブジェクト
            
        Returns:
            結果辞書
        """
        # パラメータ取得
        input_file = self.parameterAsFile(parameters, self.INPUT_DM_FILE, context)
        output_file = self.parameterAsFileOutput(parameters, self.OUTPUT_GPKG, context)
        target_crs = self.parameterAsCrs(parameters, self.TARGET_CRS, context)
        add_to_map = self.parameterAsBool(parameters, self.ADD_TO_MAP, context)
        
        # 入力ファイルチェック
        if not os.path.exists(input_file):
            raise QgsProcessingException(
                self.tr(f'Input file does not exist: {input_file}')
            )
        
        feedback.pushInfo(self.tr(f'Input DM file: {input_file}'))
        feedback.pushInfo(self.tr(f'Output GeoPackage: {output_file}'))
        
        try:
            # Step 1: DMファイル読み込み
            feedback.pushInfo(self.tr('Reading DM file...'))
            feedback.setProgress(10)
            
            if feedback.isCanceled():
                return {}
            
            records = read_dm_file(input_file)
            feedback.pushInfo(self.tr(f'Parsed {len(records)} records'))
            
            # Step 2: 地物ごとにグループ化
            feedback.pushInfo(self.tr('Grouping features...'))
            feedback.setProgress(30)
            
            if feedback.isCanceled():
                return {}
            
            grouped = group_by_features(records)
            
            # 座標系CRSの決定
            source_crs_code = grouped['zukaku']['crs_code']
            source_crs = get_crs_from_code(source_crs_code)
            
            if target_crs.isValid():
                output_crs = target_crs
                feedback.pushInfo(self.tr(f'Converting from EPSG:{source_crs.to_epsg()} to EPSG:{output_crs.authid()}'))
            else:
                output_crs = source_crs
                feedback.pushInfo(self.tr(f'Using source CRS: EPSG:{source_crs.to_epsg()}'))
            
            # Step 3: 分類コードマッピング読み込み
            feedback.pushInfo(self.tr('Loading layer name mapping...'))
            layer_names_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'data',
                '@DmLayerNameList.txt'
            )
            layer_names = load_layer_names(layer_names_file)
            
            # Step 4: GeoPackage書き込み
            feedback.pushInfo(self.tr('Writing GeoPackage...'))
            feedback.setProgress(50)
            
            if feedback.isCanceled():
                return {}
            
            write_to_geopackage(
                grouped['layers'],
                output_file,
                output_crs.authid().split(':')[1],  # EPSGコード
                layer_names,
                feedback=feedback
            )
            
            feedback.pushInfo(self.tr('GeoPackage created successfully'))
            feedback.setProgress(80)
            
            # Step 5: マップにレイヤー追加
            if add_to_map:
                feedback.pushInfo(self.tr('Adding layers to map...'))
                
                for bunrui_code in grouped['layers'].keys():
                    layer_name = f"layer_{bunrui_code}"
                    layer_display_name = f"{bunrui_code}: {layer_names.get(bunrui_code, 'Unknown')}"
                    
                    # GeoPackageレイヤーを読み込み
                    uri = f"{output_file}|layername={layer_name}"
                    layer = QgsVectorLayer(uri, layer_display_name, "ogr")
                    
                    if layer.isValid():
                        QgsProject.instance().addMapLayer(layer)
                    else:
                        feedback.pushWarning(
                            self.tr(f'Failed to load layer: {layer_name}')
                        )
                
                feedback.pushInfo(self.tr('Layers added to map'))
            
            feedback.setProgress(100)
            feedback.pushInfo(self.tr('Conversion completed successfully'))
            
            return {
                self.OUTPUT_GPKG: output_file
            }
            
        except Exception as e:
            feedback.reportError(self.tr(f'Error: {str(e)}'), fatalError=True)
            raise QgsProcessingException(str(e))
```

### 6.7 Processingプラグインの使用方法

1. **Processing Toolboxから実行**
   - Processing Toolboxを開く
   - "DM Loader" > "Converter" > "DM to GeoPackage"を選択
   - パラメータを設定して実行

2. **Pythonコンソールから実行**
```python
import processing

processing.run(
    "dm_loader:dm_to_geopackage",
    {
        'INPUT_DM_FILE': '/path/to/input.dm',
        'OUTPUT_GPKG': '/path/to/output.gpkg',
        'TARGET_CRS': 'EPSG:6677',  # オプション
        'ADD_TO_MAP': True
    }
)
```

3. **モデルデザイナーで使用**
   - 他のProcessingアルゴリズムと組み合わせてワークフロー作成が可能

4. **バッチ処理**
   - 複数のDMファイルを一括変換可能

---

## 7. テスト要件

### 7.1 テスト戦略

- **単体テスト**: 各モジュールの関数レベル
- **統合テスト**: DMファイル→GeoPackage変換の全フロー
- **カバレッジ目標**: 80%以上

### 7.2 テストケース

#### 7.2.1 parser.pyのテスト

```python
import pytest
from dm_parser.parser import read_dm_file, parse_m_record

def test_parse_m_record():
    """図郭レコードのパーステスト"""
    # 実際の84バイトデータ
    line = b'M 09OC592 2000200000000000000000000000000500000000500000' + b' ' * 26
    
    result = parse_m_record(line)
    
    assert result['record_type'] == 'M'
    assert result['zukaku_id'] == '09OC592'
    assert result['crs_code'] == 9
    assert result['datum'] == '2000'

def test_read_dm_file_not_found():
    """存在しないファイルのテスト"""
    with pytest.raises(FileNotFoundError):
        read_dm_file('/nonexistent/file.dm')
```

#### 7.2.2 coordinate.pyのテスト

```python
from dm_parser.coordinate import transform_coordinates, get_crs_from_code

def test_get_crs_from_code():
    """CRS取得のテスト"""
    crs = get_crs_from_code(9)
    assert crs.to_epsg() == 6677

def test_transform_coordinates():
    """座標変換のテスト"""
    # 平面直角座標系9系 → WGS84
    source_crs = get_crs_from_code(9)
    target_crs = CRS.from_epsg(4326)
    
    coords = [(0.0, 0.0), (1000.0, 1000.0)]
    result = transform_coordinates(coords, source_crs, target_crs)
    
    # 結果の妥当性チェック（東京付近の緯度経度）
    assert 35.0 < result[0][1] < 36.0  # 緯度
    assert 139.0 < result[0][0] < 140.0  # 経度
```

#### 7.2.3 geometry.pyのテスト

```python
from dm_parser.geometry import build_polygon_geometry, build_circle_geometry

def test_build_polygon_geometry():
    """面ジオメトリ構築のテスト"""
    element = {
        'coordinates': [
            [0.0, 0.0, None],
            [10.0, 0.0, None],
            [10.0, 10.0, None],
            [0.0, 10.0, None]
        ]
    }
    
    geom = build_polygon_geometry(element)
    
    assert geom['type'] == 'Polygon'
    assert len(geom['coordinates']) == 1  # 1つのring
    assert len(geom['coordinates'][0]) == 5  # 閉じた4角形
    assert geom['coordinates'][0][0] == geom['coordinates'][0][-1]  # 始点=終点

def test_build_circle_geometry():
    """円ジオメトリ構築のテスト"""
    element = {
        'repr_point': {'x': 100.0, 'y': 100.0, 'z': 0.0},
        'coordinates': [[110.0, 100.0, None]]  # 半径10
    }
    
    geom = build_circle_geometry(element, num_points=36)
    
    assert geom['type'] == 'Polygon'
    assert len(geom['coordinates'][0]) == 37  # 36点 + 閉じる
```

### 7.3 統合テスト

```python
def test_full_conversion():
    """DMファイル→GeoPackage変換の統合テスト"""
    # テスト用DMファイル
    dm_file = 'tests/fixtures/sample.dm'
    output_file = 'tests/output/test.gpkg'
    
    # 変換実行
    from dm_parser.parser import read_dm_file
    from dm_parser.gpkg_writer import write_to_geopackage
    
    records = read_dm_file(dm_file)
    grouped = group_by_features(records)
    
    # ... 中間処理 ...
    
    write_to_geopackage(features, output_file, 6677, layer_names)
    
    # 出力ファイルの検証
    assert os.path.exists(output_file)
    
    # QGISで読み込み可能か確認（fionaで検証）
    import fiona
    with fiona.open(output_file, layer='layer_1100') as src:
        assert len(src) > 0
        feature = next(iter(src))
        assert 'bunrui_code' in feature['properties']
```

---

## 8. 既知の制約事項

### 8.1 DMフォーマット関連

| 項目 | 制約内容 | 対処方法 |
|---|---|---|
| 文字化け | Shift-JISの特殊文字が文字化けする可能性 | errors='replace'で置換 |
| 座標精度 | mm単位→m単位変換で丸め誤差 | 十分な精度は維持される（実用上問題なし） |
| 円弧・楕円 | 正確な円弧ではなく近似 | 36点で近似（視覚的に十分） |
| 拡張DM仕様 | バージョン2の拡張機能は未対応 | 基本機能のみ実装、拡張は今後対応 |

### 8.2 GeoPackage関連

| 項目 | 制約内容 | 対処方法 |
|---|---|---|
| レイヤー名 | SQLiteの予約語は使用不可 | `layer_`プレフィックスで回避 |
| 属性名 | 一部の特殊文字は使用不可 | 英数字とアンダースコアのみ使用 |
| ファイルサイズ | 大容量DMファイルでメモリ不足の可能性 | ストリーミング処理の実装を検討 |

### 8.3 座標変換関連

| 項目 | 制約内容 | 対処方法 |
|---|---|---|
| 座標系混在 | 1ファイル内で複数座標系は非対応 | 図郭単位で処理 |
| 測地系 | JGD2000/2011の自動判定が曖昧 | 明示的にパラメータで指定可能に |

---

## 9. 実装チェックリスト

### 9.1 フェーズ1: コアパーサー

- [ ] `dm_parser/parser.py`
  - [ ] `read_dm_file()` 実装
  - [ ] `group_by_features()` 実装
- [ ] `dm_parser/records.py`
  - [ ] `parse_m_record()` 実装
  - [ ] `parse_g_record()` 実装
  - [ ] `parse_e_record()` 実装
  - [ ] `parse_r_record()` 実装
- [ ] `dm_parser/coordinate.py`
  - [ ] `get_crs_from_code()` 実装
  - [ ] `transform_coordinates()` 実装
- [ ] `dm_parser/geometry.py`
  - [ ] `build_point_geometry()` 実装
  - [ ] `build_linestring_geometry()` 実装
  - [ ] `build_polygon_geometry()` 実装
  - [ ] `build_circle_geometry()` 実装
- [ ] `dm_parser/layer_codes.py`
  - [ ] `load_layer_names()` 実装（@DmLayerNameList.txt読み込み）
- [ ] 単体テスト作成（カバレッジ80%以上）

### 9.2 フェーズ2: GeoPackageライター

- [ ] `dm_parser/gpkg_writer.py`
  - [ ] `write_to_geopackage()` 実装
  - [ ] `determine_geometry_type()` 実装
- [ ] CLIツール `main.py` 実装
- [ ] 統合テスト作成

### 9.3 フェーズ3: QGIS Processingプラグイン

- [ ] プラグイン構造セットアップ
  - [ ] `metadata.txt` 作成
  - [ ] `__init__.py` 作成（classFactory実装）
- [ ] Processing Provider実装
  - [ ] `dm_loader_provider.py` 作成
  - [ ] Provider登録・解除ロジック
- [ ] Processing Algorithm実装
  - [ ] `dm_loader_algorithm.py` 作成
  - [ ] パラメータ定義（入力DMファイル、出力GeoPackage、CRS設定等）
  - [ ] `processAlgorithm()` メソッド実装
  - [ ] フィードバック機能（進捗表示）
- [ ] PyQGIS連携
  - [ ] GeoPackageレイヤー自動追加
  - [ ] エラーハンドリングとメッセージ表示
- [ ] ユーザーマニュアル作成

---

## 10. 参考資料

### 10.1 公式ドキュメント

- 国土地理院「公共測量作業規程の準則 付録7」
- 国土地理院「公共測量標準図式 数値地形図データファイル仕様」
- OGC GeoPackage Specification 1.2

### 10.2 ライブラリドキュメント

- pyproj: https://pyproj4.github.io/pyproj/
- fiona: https://fiona.readthedocs.io/
- PyQGIS: https://qgis.org/pyqgis/

---

**このドキュメントはLLMが実装に使用するための詳細仕様書です。実装時は本仕様書を参照し、不明点があれば人間に確認してください。**
