# DM Converter

## 1. 概要

このプラグインは、DM ファイル（日本の数値地図フォーマット）を QGIS 上で GeoPackage に変換することを目的としています。

- **主な技術**: QGIS 3, Python 3.9+, PyQGIS, `uv`
- **提供者**: MIERUNE Inc., 国際航業株式会社

---

## 2. 主な機能

### DM ファイル → GeoPackage 変換

- 単一ファイルの変換、またはフォルダを指定して複数ファイルを一括変換
- 座標系番号（1〜19）から JGD2011 平面直角座標系（EPSG:6669〜6687）を自動判定
- 座標系・地図情報レベルが異なるファイルは自動スキップ
- E7 注記レイヤへのラベル表示を自動設定
- 変換ログをテキストファイルに出力（オプション）

### 対応要素タイプ

| タイプ | 内容 | ジオメトリ |
| ------ | ---- | ---------- |
| E1     | 面   | Polygon    |
| E2     | 線   | LineString |
| E3     | 円   | Polygon    |
| E4     | 円弧 | LineString |
| E5     | 点   | Point      |
| E6     | 方向 | Point      |
| E7     | 注記 | Point      |

---

## 3. アーキテクチャ

本プラグインは、以下の階層化アーキテクチャに基づいて設計しています。

```
┌──────────────────────────────────────────────┐
│  Algorithm Layer (algorithm_*.py)            │  ← 変換処理の制御・QGIS連携
├──────────────────────────────────────────────┤
│  Parser Layer (parser/)                      │  ← DMファイルの読み込み・解析
│    reader → classifier → parser → models    │
├──────────────────────────────────────────────┤
│  Writer Layer (writer/)                      │  ← GeoPackage生成・スタイル適用
│    geometry / crs / writer / style / log_writer │
└──────────────────────────────────────────────┘
```

- **Algorithm Layer**: ユーザー入力を受け取り、Parser でファイルを解析、Writer で GeoPackage を生成し、QGIS プロジェクトにレイヤを追加する
- **Parser Layer**: DM ファイルを 84 バイト固定長レコードとして読み込み、レコードを分類・解釈して構造化データ（`ParsedDM`）に変換
- **Writer Layer**: 構造化データからジオメトリを生成し、GeoPackage への書き出し・スタイル設定・ログ出力を担当

---

## 4. 主要なワークフロー

DM ファイルが QGIS プロジェクトに表示されるまでの処理の流れを示します。

1. **reader**: DM ファイルをバイナリとして読み込み、84 バイト単位のレコードに分割
2. **classifier**: レコードを種別（INDEX / MAP_SHEET / HEADER / ELEMENT / COORDINATE）に分類
3. **parser**: 分類済みレコードを解釈し、座標・属性を持つ `ParsedDM` に変換
4. **writer.create_merged_layers**: 複数の `ParsedDM` をマージして `QgsVectorLayer` を生成
5. **writer.save_to_geopackage**: `QgsVectorLayer` を GeoPackage ファイルに書き出し
6. **log_writer**: 変換結果サマリーをテキストファイルに出力（オプション）
7. **algorithm**: 生成した GeoPackage をプロジェクトに追加し、マップをズーム調整
8. **style.apply_annotation_labels**: E7 注記レイヤにラベル表示を設定

---

## 5. 開発環境のセットアップ

`uv` を使用した仮想環境の構築を推奨します。

### ステップ 1: 仮想環境の作成

QGIS にバンドルされている Python を指定して仮想環境を作成します。

```bash
# macOS の場合
uv venv --python /Applications/QGIS.app/Contents/MacOS/bin/python3 --system-site-packages

# Windows の場合（QGIS のバージョン/パスに応じて要調整）
uv venv --python "C:\Program Files\QGIS 3.x\apps\Python39\python.exe" --system-site-packages
```

_`--system-site-packages` オプションにより、QGIS の PyQGIS ライブラリ等を引き継ぎます。_

### ステップ 2: 仮想環境の有効化

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (Command Prompt)
.venv\Scripts\activate
```

### ステップ 3: 開発用ライブラリのインストール

型チェックやコード品質管理ツールをインストールします。

```bash
uv sync
```

---

## 6. プロジェクト構造

```
dmconverter/
├── __init__.py                             # プラグインエントリーポイント
├── metadata.txt                            # プラグインのメタデータ（名前、バージョンなど）
├── pyproject.toml                          # プロジェクト設定・依存関係管理（uv 用）
│
├── core/dmconverter/                       # プラグイン本体
│   ├── plugin.py                           # QGISプラグインメインクラス
│   ├── provider.py                         # Processing Toolbox プロバイダー
│   ├── algorithm_geopackage_converter.py   # DMからGeoPackageへの変換アルゴリズム
│   ├── algorithm_apply_style.py            # スタイル適用アルゴリズム
│   ├── constants.py                        # 定数・分類コード表
│   ├── schema.py                           # GeoPackage スキーマ定義
│   │
│   ├── parser/                             # DMファイル解析モジュール
│   │   ├── reader.py                       # バイナリ読み込み・エンコーディング判定
│   │   ├── classifier.py                   # レコード分類・仕分け
│   │   ├── parser.py                       # レコード解釈・データ構造化
│   │   └── models.py                       # パーサーのデータモデル定義
│   │
│   └── writer/                             # GeoPackage 生成モジュール
│       ├── writer.py                       # レイヤ作成・GeoPackage 書き出し
│       ├── geometry.py                     # 座標変換・ジオメトリ生成
│       ├── crs.py                          # 座標参照系マッピング
│       ├── style.py                        # レイヤスタイル・ラベル設定
│       └── log_writer.py                   # 変換ログ出力
│
├── imgs/
│   └── icon.png                            # プラグインアイコン
│
└── tests/                                  # テスト
    ├── unit/                               # ユニットテスト
    ├── test_metadata.py
    └── qgis_interface.py                   # テスト用 QGIS インターフェースモック
```

---

## 7. 開発ガイドライン

#### インポート

相対インポートを使用してください。

```python
# 推奨
from .models import ParsedDM
from ..writer.geometry import to_polygon_geometry

# 非推奨
from core.dmconverter.parser.models import ParsedDM
```

#### 型ヒントとドキュメント

可能な限り型アノテーションと docstring（Google スタイル）を記述してください。

```python
def get_epsg(coordinate_system: int) -> int:
    """座標系番号から EPSG コードを取得します。

    Args:
        coordinate_system (int): 平面直角座標系の系番号（1〜19）

    Returns:
        int: 対応する EPSG コード
    """
    ...
```

#### コード品質

`ruff` を使用してコードの品質を保ってください。

```bash
# リント実行
ruff check .

# 自動フォーマット
ruff format .
```
