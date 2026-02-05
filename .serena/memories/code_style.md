# Code Style and Conventions

## Design Principles
- **関数型アーキテクチャ**: 純粋関数パターン（同じ入力に常に同じ出力）
- **イミュータブルデータ**: `@dataclass(frozen=True)`を使用
- **クラス不使用**: dataclassはデータコンテナとしてのみ
- **Result型パターン**: Success/Failureでエラーハンドリング

## Type Safety
- 型ヒント必須（全関数）
- `any`/`unknown`型禁止
- TypedDictやLiteral型を活用

## Naming Conventions
| Type | Convention | Example |
|------|------------|---------|
| Files | snake_case.py | `index_record_parser.py` |
| Classes | PascalCase (dataclassのみ) | `IndexRecord` |
| Functions | snake_case（動詞で開始） | `parse_index_record_a` |
| Constants | UPPER_SNAKE_CASE | `EPSG_JGD2011` |
| Tests | test_ prefix | `test_index_record_parser.py` |

## Import Order
```python
# 1. Standard library
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

# 2. Project imports (relative import preferred)
from dmconverter.dm_parser.models import Coordinate
from dmconverter.dm_parser.record_helpers import extract_field

# 3. QGIS (conditional import)
try:
    from qgis.core import QgsVectorLayer
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False
```

## Error Handling
- 致命的エラー: 例外を発生
- 軽微なエラー: Result型で処理継続

## Testing
- pytest使用
- テスト構造: `tests/unit/`, `tests/integration/`
- サンプルデータ: `tests/sample_data/`
