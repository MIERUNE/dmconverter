# Technology Stack

## Architecture

**関数型アーキテクチャ + レイヤード構造**

```
Parser Layer → Converter Layer → Generator Layer
(純粋関数)      (座標変換)        (QGIS API)
```

- 各層は単一責務を持ち、テスト容易性と保守性を確保
- 副作用（ファイルI/O、QGIS API呼び出し）は最外層のみに局所化
- dataclass(frozen=True)によるイミュータブルデータ構造

## Core Technologies

- **Language**: Python 3.9+
- **GIS Library**: PyQGIS (QGIS 3.28+)
- **Output Format**: GeoPackage (SQLite)
- **Data Models**: dataclass (標準ライブラリ)

## Key Libraries

- **PyQGIS**: QgsVectorLayer, QgsGeometry, QgsVectorFileWriter等
- **sqlite3**: GeoPackage CRS直接設定用（標準ライブラリ）

## Development Standards

### Type Safety
- 型ヒント必須（全関数）
- クラス不使用（dataclassはデータコンテナとしてのみ）
- `any`/`unknown`型禁止

### Code Quality
- ruff: リント・フォーマット
- 純粋関数パターン（同じ入力に常に同じ出力）

### Error Handling
- Result型パターン（Success/Failure）
- 致命的エラーは例外、軽微なエラーはResult型で処理継続

### Testing
- pytest
- テスト構造: `tests/unit/`, `tests/integration/`
- サンプルDMファイル: `tests/sample_data/`

## Development Environment

### Required Tools
- uv (パッケージ管理)
- QGIS 3.28+ (Python環境)

### Common Commands
```bash
# 仮想環境作成 (macOS)
uv venv --python /Applications/QGIS.app/Contents/MacOS/bin/python3 --system-site-packages

# テスト実行
pytest tests/

# リント
ruff check .
```

## Key Technical Decisions

1. **座標系コード取得**: 図郭ID（map_sheet_id）の先頭2桁から抽出
   - 例: "02JF613" → 座標系コード = 2（第2系）

2. **測地成果区分コード取得**: インデックスレコードの53桁目以降末尾から抽出
   - 0, 1: JGD2000 / 2: JGD2011

3. **座標軸変換**: DM形式（X=北、Y=東）→ GIS形式（X=東、Y=北）にスワップ

4. **GeoPackage CRS設定**: QGIS環境未初期化時はSQLite直接操作で確実に設定

---
_Document standards and patterns, not every dependency_
