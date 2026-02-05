# Project Structure

## Organization Philosophy

**ドメイン駆動 + レイヤード構造**

DMファイル処理という単一ドメインに特化し、Parser → Converter → Generator の3層で責務を分離。

## Directory Patterns

### Core Module (`dmconverter/dm_parser/`)
**Purpose**: DMファイルパースとQGISレイヤ生成の全機能
**Pattern**: 機能別モジュール分割

| Module | Role |
|--------|------|
| `models.py` | イミュータブルデータ構造（dataclass） |
| `errors.py` | Result型とエラー定義 |
| `record_helpers.py` | フィールド抽出ヘルパー |
| `index_record_parser.py` | インデックスレコードパース |
| `map_sheet_parser.py` | 図郭レコードパース |
| `element_parser.py` | 要素レコードパース |
| `file_parser.py` | ファイル全体のパース統合 |
| `coordinate.py` | 座標系・EPSG変換 |
| `geometry.py` | QGISジオメトリ生成 |
| `classification.py` | 分類コードマッピング |
| `layer_generator.py` | QgsVectorLayer生成 |
| `api.py` | 公開API関数 |

### Test Suite (`tests/`)
**Purpose**: 単体テストと統合テスト
**Pattern**: テスト種別で分離

```
tests/
├── unit/           # 各モジュールの単体テスト
├── integration/    # エンドツーエンドテスト
└── sample_data/    # テスト用DMファイル・GeoJSON
```

### Specifications (`.kiro/specs/`)
**Purpose**: 仕様ドキュメント（要件・設計・タスク）
**Pattern**: 機能単位でサブディレクトリ

## Naming Conventions

- **Files**: snake_case.py（例: `index_record_parser.py`）
- **Classes**: データコンテナのみ、PascalCase dataclass（例: `IndexRecord`）
- **Functions**: snake_case、動詞で始まる（例: `parse_index_record_a`）
- **Constants**: UPPER_SNAKE_CASE（例: `EPSG_JGD2011`）
- **Tests**: `test_` prefix（例: `test_index_record_parser.py`）

## Import Organization

```python
# 標準ライブラリ
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

# プロジェクト内（相対インポート推奨）
from dmconverter.dm_parser.models import Coordinate
from dmconverter.dm_parser.record_helpers import extract_field

# QGIS（条件付きインポート）
try:
    from qgis.core import QgsVectorLayer
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False
```

**Key Pattern**: QGIS依存はtry/exceptでラップし、非QGIS環境でもパース機能は動作可能に。

## Code Organization Principles

1. **純粋関数優先**: 副作用はGenerator層に局所化
2. **イミュータブルデータ**: `@dataclass(frozen=True)`
3. **Result型エラーハンドリング**: 例外は致命的エラーのみ
4. **相対インポート**: Plugin Reloader互換性のため推奨

---
_Document patterns, not file trees. New files following patterns shouldn't require updates_
