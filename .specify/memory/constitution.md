<!--
## Sync Impact Report

Version change: 1.0.1 → 1.1.0
Modified sections:
  - II. QGIS API Compliance: Added mandatory methods (createInstance, name, displayName)
  - II. QGIS API Compliance: Clarified output parameter types
  - II. QGIS API Compliance: Added feedback.isCanceled() check requirement
  - II. QGIS API Compliance: Added group/groupId methods
  - Technical Standards: Added algorithm template structure

Added sections: None
Removed sections: None

Templates requiring updates:
  - .specify/templates/plan-template.md ✅ (no updates required - generic template)
  - .specify/templates/spec-template.md ✅ (no updates required - generic template)
  - .specify/templates/tasks-template.md ✅ (no updates required - generic template)

Follow-up TODOs: None
Validation source: Context7 MCP (QGIS Python API, QGIS Documentation)
-->

# DM Converter QGIS Plugin Constitution

## Core Principles

### I. Processing Algorithm First

すべての地理空間処理機能は `QgsProcessingAlgorithm` として実装しなければならない（MUST）。

- アルゴリズムは自己完結型で、独立してテスト可能でなければならない
- 各アルゴリズムは単一の明確な目的を持たなければならない
- アルゴリズムは QGIS Processing Framework を通じて公開しなければならない
- バッチ処理とモデルビルダーとの互換性を確保しなければならない

**根拠**: Processing形式はQGISエコシステムとの最大の互換性を提供し、
ユーザーがGUIとPython双方から機能にアクセスすることを可能にする。

### II. QGIS API Compliance

QGIS APIの規約とベストプラクティスに従わなければならない（MUST）。

#### 必須メソッド（MUST実装）

すべての `QgsProcessingAlgorithm` サブクラスは以下のメソッドを実装しなければならない：

- `createInstance()` - アルゴリズムの新しいインスタンスを返す
- `name()` - 一意のアルゴリズム識別子を返す（ローカライズ不可）
- `displayName()` - ローカライズされた表示名を返す
- `initAlgorithm(config)` - パラメータと出力を定義する
- `processAlgorithm(parameters, context, feedback)` - 処理ロジックを実装する

#### 推奨メソッド（SHOULD実装）

- `group()` / `groupId()` - アルゴリズムのグループ化
- `shortHelpString()` - ヘルプドキュメント

#### パラメータと出力

- 入力パラメータは `QgsProcessingParameter*` サブクラスを使用すること
  - 例: `QgsProcessingParameterFeatureSource`, `QgsProcessingParameterNumber`
- 出力は `QgsProcessingParameterFeatureSink`, `QgsProcessingParameterRasterDestination` 等を使用すること
- 計算結果の出力には `QgsProcessingOutputNumber` 等を使用すること

#### フィードバックとキャンセル処理

- `feedback.setProgress(0-100)` を使用して進捗を報告すること
- ループ内で `feedback.isCanceled()` を定期的にチェックし、キャンセル時は早期終了すること
- `feedback.pushInfo()` でユーザーに情報を通知すること
- エラー時は `QgsProcessingException` を発生させること

#### その他の規約

- `QgsProcessingContext` を適切に使用してレイヤ管理を行うこと
- 相対インポート（`.module`形式）を使用して Plugin Reloader との互換性を確保すること

**根拠**: API準拠により、QGISの将来のバージョンとの互換性とプラグインの安定性が保証される。

### III. Test-Driven Development

テストは実装前に作成されなければならない（MUST）。

- 各アルゴリズムに対してユニットテストを作成すること
- テストは実装前に失敗することを確認すること（Red-Green-Refactor）
- `qgis.testing` フレームワークを使用してQGIS固有の機能をテストすること
- テストデータは `tests/data/` ディレクトリに配置すること

**根拠**: TDDにより、要件が明確に定義され、リグレッションが防止される。

### IV. Type Safety

Pythonの型ヒントを全てのコードで使用しなければならない（MUST）。

- 関数シグネチャには戻り値の型を含めること
- `Any` や `Unknown` 型の使用を禁止する
- 複雑なデータ構造には `TypedDict` や `dataclass` を使用すること
- 型チェックには `pyright` または `mypy` を使用すること

**根拠**: 型ヒントはIDEのサポートを向上させ、実行前にバグを発見することを可能にする。

### V. Simplicity

YAGNIの原則に従い、最小限の複雑さを維持しなければならない（MUST）。

- ハードコーディングは絶対に必要な場合を除き避けること
- クラスは `Error` の拡張など、絶対に必要な場合のみ使用すること
- 単一責任の原則を守ること
- 仮想的な将来の要件のための設計は行わないこと

**根拠**: シンプルなコードは保守が容易で、バグが少なく、理解しやすい。

## Technical Standards

### 技術スタック

- **Python バージョン**: QGIS同梱のPython（3.9以上）
- **QGIS バージョン**: QGIS 3.x（LTR以上を推奨）
- **テスト**: pytest + qgis.testing
- **型チェック**: pyright
- **リンター**: ruff
- **フォーマッター**: ruff format

### プロジェクト構造

```text
dmconverter/
├── __init__.py              # Plugin entry point
├── plugin.py                # Plugin class (initProcessing, unload)
├── processing/
│   ├── __init__.py
│   ├── provider.py          # QgsProcessingProvider
│   └── algorithms/          # Individual algorithms
│       ├── __init__.py
│       └── *.py
├── tests/
│   ├── __init__.py
│   ├── data/                # Test data files
│   └── test_*.py
└── metadata.txt             # Plugin metadata
```

### アルゴリズムテンプレート

```python
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink,
)

class MyAlgorithm(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'

    def createInstance(self):
        return MyAlgorithm()

    def name(self) -> str:
        return 'myalgorithm'

    def displayName(self) -> str:
        return self.tr('My Algorithm')

    def group(self) -> str:
        return self.tr('DM Converter')

    def groupId(self) -> str:
        return 'dmconverter'

    def initAlgorithm(self, config=None) -> None:
        self.addParameter(...)

    def processAlgorithm(self, parameters, context, feedback):
        for current, feature in enumerate(features):
            if feedback.isCanceled():
                break
            # 処理ロジック
            feedback.setProgress(int(current * total))
        return {self.OUTPUT: dest_id}
```

### プラグイン登録パターン

```python
from qgis.core import QgsApplication
from .processing.provider import Provider

class Plugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None

    def initProcessing(self):
        self.provider = Provider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)
```

### コーディング規約

- 相対インポートを使用すること（`from .module import X`）
- アルゴリズム名は `tr()` でラップして国際化対応すること
- エラーメッセージはユーザーにとって意味のあるものにすること
- ログは `QgsMessageLog` を使用すること

## Development Workflow

### ローカルテスト実行

ローカルでテストを実行する際は、QGIS同梱のPythonを使用しなければならない（MUST）。

**macOS:**

```bash
/Applications/QGIS.app/Contents/MacOS/bin/python3 -m pytest
```

**根拠**: QGISプラグインは `qgis.core`、`qgis.gui` などのQGISモジュールに依存するため、
QGIS同梱のPythonインタープリターを使用しなければテストを正常に実行できない。

### コードレビュー要件

- すべてのPRはレビューを受けなければならない
- Constitution準拠をレビュー時に確認すること
- テストがパスしていることを確認すること
- 型チェックがパスしていることを確認すること

### 品質ゲート

実装完了前に以下を確認すること：

1. `ruff check` がエラーなしでパスすること
2. `ruff format --check` がパスすること
3. `pyright` がエラーなしでパスすること
4. `/Applications/QGIS.app/Contents/MacOS/bin/python3 -m pytest` がパスすること

### ブランチ戦略

- `main`: 安定版リリース
- `feature/*`: 新機能開発
- `fix/*`: バグ修正

## Governance

### 憲法の優先順位

この憲法はプロジェクトの他のすべてのプラクティスに優先する。

### 修正手続き

1. 修正提案を文書化すること
2. チームの承認を得ること
3. 移行計画を作成すること
4. バージョンを更新すること

### バージョニングポリシー

- **MAJOR**: 後方互換性のない原則の削除または再定義
- **MINOR**: 新しい原則またはセクションの追加
- **PATCH**: 明確化、表現の修正、非意味的な改善

### コンプライアンスレビュー

- すべてのPR/レビューで準拠を確認すること
- 複雑さは正当化されなければならない
- 違反は修正されるまでマージしないこと

**Version**: 1.1.0 | **Ratified**: 2026-02-04 | **Last Amended**: 2026-02-04
