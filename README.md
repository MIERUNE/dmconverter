# DM Converter

## 1. 概要

このプラグインは、DMファイル（日本の数値地図フォーマット）をQGIS上でGeoPackageに変換することを目的としています。

- **主な技術**: QGIS3, Python3.9+, PyQGIS, `uv`
- **提供者**: MIERUNE Inc., 国際航業株式会社

---

## 2. 主な機能

### DM ファイル → GeoPackage 変換

- 単一ファイルの変換、またはフォルダを指定して複数ファイルを一括変換
- 座標系番号（1〜19）からJGD2011平面直角座標系を自動判定
- 座標系・地図情報レベルが異なるファイルは自動スキップ
- E7 注記レイヤへのラベル表示を自動設定
- 変換ログをテキストファイルに出力（オプション）

### QML スタイルファイル

スタイル適用アルゴリズムでは、外部のQMLファイルをジオメトリタイプ（点・線・面）ごとに1つずつ用意して使用します。

QML ファイルの要件：

- **レンダラー**: `categorizedSymbol`（カテゴリ分け）
- **分類フィールド**: `HCODE2`（分類コード4桁 + 図形区分の文字列）
- **カテゴリ値**: `HCODE2` の値に対してシンボルを割り当て

QML からレイヤへ適用される内容：

- **レンダラー**（シンボロジ）: 注記（E7）以外のレイヤに適用
- **属性フォーム設定**（QGIS のスタイルカテゴリ `Fields` / `Forms`）: ウィジェット種別（バリューマップ・範囲など）・別名・デフォルト値式・制約・編集可否・labelOnTop 等。注記レイヤを含む同一ジオメトリタイプの全レイヤに適用され、出力される QLR にも含まれます。QML にあってレイヤに存在しないフィールドの設定は無視されます。
- **注意**: フォーム設定を含む QML も、上記の要件（`categorizedSymbol` レンダラーで `HCODE2` をカテゴリ分け）を満たす必要があります。レンダラーが無い QML は検出されず、フォーム設定も適用されません。

QGIS 上でスタイルを作成・調整し、レイヤプロパティから `.qml` としてエクスポートしたものを使用してください。

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

- **Algorithm Layer**: ユーザー入力を受け取り、Parser でファイルを解析、Writer で GeoPackage を生成し、QGISプロジェクトにレイヤを追加する
- **Parser Layer**: DM ファイルを 84バイト固定長レコードとして読み込み、レコードを分類・解釈して構造化データ（`ParsedDM`）に変換
- **Writer Layer**: 構造化データからジオメトリを生成し、GeoPackageへの書き出し・スタイル設定・ログ出力を担当

---

## 4. 主要なワークフロー

DM ファイルが QGIS プロジェクトに表示されるまでの処理の流れを示します。

1. **reader**: DM ファイルをバイナリとして読み込み、84バイト単位のレコードに分割
2. **classifier**: レコードを種別（INDEX / MAP_SHEET / HEADER / ELEMENT / COORDINATE）に分類
3. **parser**: 分類済みレコードを解釈し、座標・属性を持つ `ParsedDM` に変換
4. **writer.create_merged_layers**: 複数の `ParsedDM` をマージして `QgsVectorLayer` を生成
5. **writer.save_to_geopackage**: `QgsVectorLayer` を GeoPackage ファイルに書き出し
6. **log_writer**: 変換結果サマリーをテキストファイルに出力（オプション）
7. **algorithm**: 生成した GeoPackage をプロジェクトに追加し、マップをズーム調整
8. **style.apply_layer_style**: E7 注記レイヤにラベル表示を設定し、スタイルフォルダ指定時は QML のレンダラーと属性フォーム設定を適用

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
├── core/dmconverter/                 # プラグイン本体
│   ├── plugin.py                     # QGISプラグインメインクラス
│   ├── provider.py                   # Processing Toolbox プロバイダー
│   ├── algorithm_geopackage_converter.py  # DM→GeoPackage 変換アルゴリズム
│   ├── algorithm_apply_style.py      # スタイル適用アルゴリズム
│   ├── constants.py                  # 定数・分類コード表
│   ├── schema.py                     # GeoPackage スキーマ定義
│   ├── parser/                       # DMファイル解析（reader / classifier / parser / models）
│   └── writer/                       # GeoPackage 生成（writer / geometry / crs / style / log_writer）
├── tests/                            # テスト（unit / data）
├── imgs/                             # アイコン画像
├── metadata.txt
└── pyproject.toml
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
