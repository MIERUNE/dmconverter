# Requirements Document

## Project Description (Input)
docs/公共測量標準図式_数値地形図データファイル仕様.pdfで定義されるDMファイルをparseして、pyqgisでベクタレイヤに変換するモジュールを作りたいです。

## Introduction
本ドキュメントは、公共測量標準図式で定義される数値地形図データファイル（DMファイル）をパースし、PyQGISのベクタレイヤに変換するPythonモジュールの要件を定義する。DMファイルはFORTRAN形式の固定長80バイトレコードで構成され、地形図データ（点・線・面・円・円弧・注記・属性）を格納する。本モジュールはQGIS環境でのDMデータ活用を可能にする。

## Requirements

### Requirement 1: DMファイルパース機能
**Objective:** As a GIS技術者, I want DMファイルを読み込んでデータ構造に変換する機能, so that DMファイルの内容をプログラムで利用できる。

#### Acceptance Criteria
1. When DMファイルパスが指定された場合, the DM Parser shall ファイルを読み込み、全レコードをパースしてデータオブジェクトに変換する。
2. The DM Parser shall インデックスレコード(a)(b)(c)をパースして、計画機関名・座標系・図郭情報・使用分類コードを抽出する。
3. The DM Parser shall 図郭レコード(a)〜(f)をパースして、図郭識別番号・図郭名称・座標範囲・作成情報を抽出する。
4. The DM Parser shall グループヘッダレコード（レイヤヘッダ・要素グループヘッダ）をパースして、地図分類コード・階層レベル・要素数を抽出する。
5. The DM Parser shall 要素レコードをパースして、分類コード・データタイプ（E1〜E8）・座標・属性を抽出する。
6. The DM Parser shall 3次元座標レコード（X, Y, Z）および2次元座標レコード（X, Y）をパースして座標値を抽出する。
7. The DM Parser shall 注記レコードをパースして、縦横区分・文字列方向・字大・字隔・注記データを抽出する。
8. The DM Parser shall 属性レコードをパースしてユーザー定義属性データを抽出する。

### Requirement 2: 座標系・座標値処理
**Objective:** As a GIS技術者, I want DMファイルの座標系と座標値を正しく処理する機能, so that 正確な地理座標でベクタレイヤを作成できる。

#### Acceptance Criteria
1. The DM Parser shall インデックスレコードの座標系コードと図郭レコードの測地成果区分コードから平面直角座標系（第1系〜第19系）および測地系（JGD2011/JGD2000）を判定する。
2. The DM Parser shall 図郭レコードの座標値の単位（m/cm/mm）を地図情報レベルに基づいて判定する。
3. When 座標値の単位が「1」（m単位）の場合, the DM Parser shall 座標値をそのままメートル単位として処理する。
4. When 座標値の単位が「10」（cm単位）の場合, the DM Parser shall 座標値を100で除算してメートル単位に変換する。
5. When 座標値の単位が「999」（mm単位）の場合, the DM Parser shall 座標値を1000で除算してメートル単位に変換する。
6. When Z座標が存在しない場合（値が-999/-99900/-999000）, the DM Parser shall 該当座標を2次元として処理する。

### Requirement 3: ジオメトリ変換機能
**Objective:** As a GIS技術者, I want DMファイルの各データタイプをQGISジオメトリに変換する機能, so that ベクタレイヤとして可視化・編集できる。

#### Acceptance Criteria
1. When データタイプがE1（面）の場合, the Geometry Converter shall 座標列からQgsPolygonジオメトリを生成する。
2. When データタイプがE2（線）の場合, the Geometry Converter shall 座標列からQgsLineStringジオメトリを生成する。
3. When データタイプがE3（円）の場合, the Geometry Converter shall 3点の座標から円を計算し、QgsPolygonまたはQgsCircularStringジオメトリを生成する。
4. When データタイプがE4（円弧）の場合, the Geometry Converter shall 始点・任意点・終点の3座標からQgsCircularStringジオメトリを生成する。
5. When データタイプがE5（点）の場合, the Geometry Converter shall 座標からQgsPointジオメトリを生成する。
6. When データタイプがE6（方向）の場合, the Geometry Converter shall 中心点と方向を示す2点ペアからQgsPointジオメトリと方向属性を生成する。
7. When Z座標が有効な値を持つ場合, the Geometry Converter shall 3次元ジオメトリ（QgsPoint, QgsLineString, QgsPolygonのZ座標付き）を生成する。

### Requirement 4: ベクタレイヤ生成機能
**Objective:** As a GIS技術者, I want DMデータをPyQGISベクタレイヤに変換する機能, so that QGISプロジェクトで地形図データを活用できる。

#### Acceptance Criteria
1. The Layer Generator shall 分類コード（取得分類コード）ごとにグループ化されたベクタレイヤを生成する。
2. The Layer Generator shall ジオメトリタイプ（Point/LineString/Polygon）ごとに分離されたレイヤを生成する。
3. The Layer Generator shall 各フィーチャに分類コード・項目名・階層レベル・取得年月を属性として付与する。
4. The Layer Generator shall 注記データ（E7）を含むフィーチャに文字列・字大・字隔・方向属性を付与する。
5. The Layer Generator shall 属性データ（E8）を含むフィーチャにユーザー定義属性を付与する。
6. The Layer Generator shall 座標系情報と測地系に基づいて適切なCRS（JGD2011: EPSG:6669〜6687、JGD2000: EPSG:2443〜2461）をレイヤに設定する。
7. When メモリレイヤとして生成する場合, the Layer Generator shall QgsVectorLayerをmemory providerで作成する。
8. When ファイル出力する場合, the Layer Generator shall GeoPackage形式でレイヤを保存する。

### Requirement 5: 分類コードマッピング
**Objective:** As a GIS技術者, I want 取得分類コードを人間が理解できる名称にマッピングする機能, so that レイヤ名や属性値が分かりやすくなる。

#### Acceptance Criteria
1. The DM Parser shall 取得分類コード表（附属資料）に基づいて、コードから項目名への変換テーブルを提供する。
2. When 分類コードが標準コード表に存在する場合, the DM Parser shall 対応する項目名（例: "21 01" → "道路縁"）を返す。
3. When 分類コードが標準コード表に存在しない場合, the DM Parser shall インデックスレコード(c)の内容記述を参照するか、コードをそのまま返す。
4. The DM Parser shall 大分類（行政界・交通施設・建物等）によるグルーピング情報を提供する。

### Requirement 6: エラーハンドリング
**Objective:** As a 開発者, I want 不正なDMファイルや予期しないデータに対する適切なエラー処理, so that 堅牢なパース処理を実現できる。

#### Acceptance Criteria
1. If ファイルが存在しない場合, the DM Parser shall FileNotFoundErrorを発生させ、ファイルパスを含むエラーメッセージを提供する。
2. If ファイルがDM形式でない場合（インデックスレコードが存在しない）, the DM Parser shall InvalidDMFileErrorを発生させる。
3. If レコードが80バイト未満の場合, the DM Parser shall 警告をログ出力し、可能な範囲でパースを継続する。
4. If 座標値が数値に変換できない場合, the DM Parser shall 警告をログ出力し、該当座標をスキップする。
5. If 未知のレコードタイプが検出された場合, the DM Parser shall 警告をログ出力し、該当レコードをスキップして処理を継続する。
6. The DM Parser shall パース結果のサマリー（成功レコード数・スキップレコード数・エラー数）を提供する。

### Requirement 7: API設計
**Objective:** As a 開発者, I want シンプルで使いやすいPython APIを提供する, so that 他のアプリケーションから容易に利用できる。

#### Acceptance Criteria
1. The DM Parser Module shall `parse_dm_file(file_path: str) -> DMData` 関数を提供し、DMファイルをパースしてデータオブジェクトを返す。
2. The DM Parser Module shall `dm_to_layers(dm_data: DMData) -> list[QgsVectorLayer]` 関数を提供し、パース結果をベクタレイヤリストに変換する。
3. The DM Parser Module shall `load_dm_to_qgis(file_path: str, add_to_project: bool = True) -> list[QgsVectorLayer]` 関数を提供し、ファイル読み込みからレイヤ追加までを一括実行する。
4. The DMData class shall 図郭情報・要素データ・座標系情報へのアクセサメソッドを提供する。
5. The DM Parser Module shall Python 3.9以上およびQGIS 3.28以上との互換性を維持する。
