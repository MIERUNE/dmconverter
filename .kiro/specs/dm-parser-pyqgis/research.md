# Research & Design Decisions

## Summary
- **Feature**: `dm-parser-pyqgis`
- **Discovery Scope**: New Feature (greenfield)
- **Key Findings**:
  - DMファイルはFORTRAN形式の固定長80バイトレコードで構成され、12種類のレコードタイプを持つ
  - PyQGISはメモリプロバイダによるベクタレイヤ作成、QgsCircularStringによる曲線ジオメトリをサポート
  - 平面直角座標系（JGD2011）はEPSG:6669〜6687でQGISに対応

## Research Log

### DMファイルフォーマット構造
- **Context**: 公共測量標準図式の数値地形図データファイル仕様書を解析
- **Sources Consulted**: docs/公共測量標準図式_数値地形図データファイル仕様.pdf
- **Findings**:
  - レコード長: 固定80バイト（FORTRAN形式）
  - 文字コード: 半角英数字、漢字（JIS第1・第2水準）
  - レコードタイプ:
    1. インデックスレコード(a)(b)(c) - ファイルメタデータ
    2. 図郭レコード(a)〜(f) - 図郭境界・座標情報
    3. グループヘッダレコード - レイヤ・要素グループ情報
    4. 要素レコード - 地物データ本体
    5. 3次元座標レコード - X, Y, Z座標値
    6. 2次元座標レコード - X, Y座標値
    7. 注記レコード - テキストデータ
    8. 属性レコード - ユーザー定義属性
  - データタイプ: E1(面), E2(線), E3(円), E4(円弧), E5(点), E6(方向), E7(注記), E8(属性)
- **Implications**:
  - パーサーは状態機械パターンで実装し、レコードタイプに応じた処理を分岐
  - 固定長レコードのため、文字列スライスによるフィールド抽出が可能

### PyQGIS ベクタレイヤ生成API
- **Context**: QGISでのメモリレイヤ作成方法を調査
- **Sources Consulted**: Context7 MCP (`/websites/qgis_pyqgis_master`)
- **Findings**:
  - メモリレイヤ作成: `QgsVectorLayer("point?crs=epsg:4326&field=id:integer", "name", "memory")`
  - ジオメトリタイプ指定: point, linestring, polygon, multipoint, multilinestring, multipolygon
  - フィールド定義: `field=name:type(length,precision)` でURLパラメータとして指定
  - フィーチャ追加: `QgsVectorLayerUtils.createFeature()` または `layer.dataProvider().addFeatures()`
  - CRS設定: `QgsCoordinateReferenceSystem.fromEpsgId(epsg_code)` → `layer.setCrs(crs)`
- **Implications**:
  - 分類コード×ジオメトリタイプごとにメモリレイヤを生成する設計が適切
  - フィールド定義はレイヤ作成時にURI形式で指定可能

### PyQGIS ジオメトリ生成API
- **Context**: 各データタイプ（点・線・面・円・円弧）のジオメトリ変換方法を調査
- **Sources Consulted**: Context7 MCP (`/websites/qgis_pyqgis_master`)
- **Findings**:
  - 点: `QgsGeometry.fromPoint(QgsPoint(x, y, z))` または `QgsGeometry.fromPointXY(QgsPointXY(x, y))`
  - 線: `QgsGeometry.fromPolyline([QgsPoint(...), ...])` - Z/M次元を自動継承
  - 面: `QgsGeometry.fromPolygonXY([[QgsPointXY(...), ...]])` - リストのリスト形式
  - 円弧: `QgsCircularString(p1, p2, p3)` - 3点通過で構築
  - 円弧(中心指定): `QgsCircularString.fromTwoPointsAndCenter(p1, p2, center, useShortestArc)`
  - 円: `QgsCircle` → `toCircularString()` で変換可能
- **Implications**:
  - E3(円)は3点から外接円を計算し、QgsCircularStringで表現
  - E4(円弧)は直接QgsCircularString(始点, 中間点, 終点)で構築可能
  - 3次元座標はQgsPointのZ値として保持される

### 座標系・EPSG対応
- **Context**: 日本の平面直角座標系（JGD2011/JGD2000）のEPSGコード対応を確認
- **Sources Consulted**: EPSG Registry, QGIS CRS Database, 国土地理院技術資料
- **Findings**:
  - JGD2011平面直角座標系: EPSG:6669〜6687（第1系〜第19系）
  - JGD2000平面直角座標系: EPSG:2443〜2461（第1系〜第19系）
  - **座標系コードの取得方法**（実装検証済み）:
    - 図郭ID（map_sheet_id）の先頭2桁が座標系コードを示す
    - 例: "02JF613" → 座標系コード = 2（第2系）
    - 例: "01AB123" → 座標系コード = 1（第1系）
  - **測地成果区分コードの取得方法**（実装検証済み）:
    - インデックスレコード(a)の53桁目以降の末尾数字から取得
    - 通常3桁で、2桁目が測地成果区分コード
    - 0, 1: JGD2000（日本測地系2000）
    - 2: JGD2011（日本測地系2011）
    - 古いデータはデフォルトでJGD2000として処理
  - 座標値の単位は地図情報レベルに依存（500/1000→m単位、2500/5000→cm単位、10000〜→mm単位）
- **Implications**:
  - 座標系コードは図郭IDの先頭2桁から抽出（数値として解釈、1-19の範囲）
  - 測地成果区分コードはインデックスレコードの末尾から抽出
  - 座標系コード×測地系→EPSGコードの2次元マッピングテーブルを実装
  - 座標値は必ずメートル単位に正規化してからジオメトリを構築

### GeoPackage出力
- **Context**: ベクタレイヤのファイル保存方法を調査
- **Sources Consulted**: Context7 MCP (`/qgis/qgis-documentation`)
- **Findings**:
  - `QgsVectorFileWriter.writeAsVectorFormatV3(layer, path, transform_context, save_options)`
  - `SaveVectorOptions`でフォーマット・レイヤ名・CRS変換等を制御
  - 同一GeoPackageへの複数レイヤ追加が可能
  - エラーハンドリング: 戻り値のタプルで成功/失敗を判定
  - **CRS設定の注意点**（実装検証済み）:
    - QGIS環境が完全に初期化されていない場合、CRSが正しく書き込まれない場合がある
    - GeoPackageはSQLite形式のため、直接SQLiteで以下のテーブルを更新可能:
      - `gpkg_spatial_ref_sys`: CRS定義の追加
      - `gpkg_geometry_columns`: srs_idの更新
      - `gpkg_contents`: srs_idの更新
    - メモリレイヤ作成時は`layer.setCrs(crs)`を明示的に呼び出すことで確実にCRSを設定
- **Implications**:
  - GeoPackage形式で複数レイヤを1ファイルに集約可能
  - 分類コードごとのレイヤを1つのGeoPackageに出力する設計が適切
  - CRS設定は複数箇所で冗長に行い、確実性を担保する

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| レイヤードアーキテクチャ | Parser → Converter → Layer Generator の3層構造 | 責務分離が明確、テスト容易 | 層間インターフェース設計が必要 | **採用** - シンプルで理解しやすい |
| パイプライン | 各処理をパイプラインステージとして連結 | 拡張性高い | 小規模プロジェクトには過剰 | 不採用 |
| プラグイン | 各レコードタイプをプラグインとして実装 | 拡張性最大 | 初期実装コスト高 | 将来の拡張時に検討 |

## Design Decisions

### Decision: レイヤードアーキテクチャの採用
- **Context**: DMファイルのパース、ジオメトリ変換、レイヤ生成を分離したい
- **Alternatives Considered**:
  1. モノリシック - 全処理を1モジュールに集約
  2. レイヤード - Parser/Converter/Generator の3層分離
  3. イベント駆動 - レコードごとにイベント発行
- **Selected Approach**: レイヤードアーキテクチャ（3層）
- **Rationale**:
  - 各層の責務が明確（パース→変換→出力）
  - 単体テストが容易（モック注入可能）
  - PyQGIS依存をGenerator層に局所化
- **Trade-offs**:
  - メリット: テスト容易性、保守性、責務分離
  - デメリット: 層間インターフェース定義のオーバーヘッド
- **Follow-up**: インターフェース定義をdataclassで型安全に実装

### Decision: 関数型設計の採用
- **Context**: 保守性・テスト容易性・副作用の局所化を重視したい
- **Alternatives Considered**:
  1. OOP（クラスベース） - 状態とメソッドを結合
  2. 関数型 - 純粋関数＋イミュータブルデータ
  3. ハイブリッド - データはクラス、処理は関数
- **Selected Approach**: 関数型設計（純粋関数＋dataclass）
- **Rationale**:
  - 純粋関数はテストが容易（入力→出力のみ検証）
  - 副作用をI/O境界に局所化できる
  - dataclass(frozen=True)でイミュータブル性を保証
  - Pythonの関数型機能（map, filter, functools）と親和性が高い
- **Trade-offs**:
  - メリット: テスト容易、並列化容易、状態管理シンプル
  - デメリット: 一部の処理で冗長になる可能性
- **Design Principles**:
  - クラスは使用しない（dataclassはデータコンテナとしてのみ使用）
  - 全ての処理は純粋関数として実装
  - 副作用（ファイルI/O、QGIS API呼び出し）は最外層に局所化
  - 高階関数・パイプライン処理を活用

### Decision: dataclassによるデータモデル
- **Context**: パース結果を型安全に表現したい
- **Alternatives Considered**:
  1. 辞書（dict） - 柔軟だが型安全性なし
  2. TypedDict - 型ヒントあるが実行時検証なし
  3. dataclass - 型ヒント＋自動生成メソッド
  4. Pydantic - バリデーション機能付き
- **Selected Approach**: dataclass（`@dataclass(frozen=True)`）
- **Rationale**:
  - 標準ライブラリで追加依存なし
  - 型ヒントによる静的解析対応
  - frozen=Trueでイミュータブル保証
  - データコンテナとしてのみ使用（メソッドは持たない）
- **Trade-offs**:
  - メリット: 軽量、標準ライブラリ、型安全、イミュータブル
  - デメリット: バリデーション機能はPydanticより弱い
- **Follow-up**: バリデーションは別途純粋関数として実装

### Decision: 分類コード×ジオメトリタイプ別レイヤ生成
- **Context**: DMデータをどのようにベクタレイヤに分割するか
- **Alternatives Considered**:
  1. 1ファイル1レイヤ - 全データを1レイヤに
  2. 分類コード別 - 分類コードごとにレイヤ分割
  3. 分類コード×ジオメトリタイプ別 - さらにジオメトリタイプで分割
- **Selected Approach**: 分類コード×ジオメトリタイプ別
- **Rationale**:
  - QGISはレイヤ単位でジオメトリタイプが単一である必要がある
  - GIS解析では同一分類の地物をまとめて扱うことが多い
  - レイヤ名で分類がわかりやすい
- **Trade-offs**:
  - メリット: QGIS互換、分析しやすい、視認性良好
  - デメリット: レイヤ数が多くなる可能性
- **Follow-up**: レイヤグループによる整理機能を検討

## Risks & Mitigations
- **文字コード問題** — DMファイルはShift_JIS/EUC-JPの可能性あり → エンコーディング自動検出またはオプション指定
- **大容量ファイル** — メモリ不足リスク → ストリーミングパースを検討
- **不正データ** — パース失敗リスク → 警告ログ＋スキップで継続処理
- **QGIS APIバージョン差異** — 3.28以上を対象とし、非推奨API使用を避ける

## Design Verification (External Article)
- **Source**: https://takamoto.biz/2020/06/都市計画ｇｉｓの構築３∨dmデータの変換/
- **Verification Date**: 2026-02-05
- **Findings**:
  1. **レコード長**: 記事では84バイト（CR+LF含むと87バイト）と記載。公式仕様では80バイトが正しく、差分は改行コード分。実装では改行コードを除去して80バイトデータとして処理する。
  2. **相対座標**: DMファイルの座標値は「図郭左下座標からの相対値」として格納される。絶対座標への変換には図郭レコード(e)の左下座標を加算する必要がある。→ **設計にto_absolute_coordinate関数を追加**
  3. **修正履歴**: DMファイルには修正履歴レコードが含まれることがある。履歴管理コードを確認してスキップする必要がある。→ **設計にis_modification_history_record関数を追加**
  4. **E1/E2区別**: 記事ではE1（面）とE2（線）の区別を明示。現設計で適切に分離されており問題なし。
- **Design Updates Made**:
  - Technical Notesセクション追加（レコード長、座標系、修正履歴の技術的説明）
  - MapSheetRecordにbase_coordinateフィールド追加
  - to_absolute_coordinate関数追加
  - is_modification_history_record、should_skip_record関数追加

## References
- [QGIS Python API Documentation](https://qgis.org/pyqgis/master/) — PyQGIS公式リファレンス
- [公共測量標準図式](https://www.gsi.go.jp/ENGLISH/page_e30026.html) — 国土地理院仕様書
- [JGD2011 EPSG Codes](https://epsg.io/?q=JGD2011) — 平面直角座標系EPSGコード一覧
