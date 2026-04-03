"""QgsProcessingAlgorithm: DM→GeoPackage変換アルゴリズム

入力: DMファイル選択 or フォルダ指定
出力: GeoPackageファイル
"""

import glob
import os
from collections import Counter

from qgis.core import (
    QgsCoordinateTransform,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsRectangle,
    QgsVectorLayer,
)

from .classifier import classify
from .constants import get_classification_name
from .parser.parser import parse
from .reader import read_records
from .writer import create_merged_layers, save_to_geopackage

# 現在変換対応している要素タイプ
_SUPPORTED_TYPES = {"E1", "E2", "E5"}


class DmToGeoPackageAlgorithm(QgsProcessingAlgorithm):
    INPUT_FILES = "INPUT_FILES"
    INPUT_FOLDER = "INPUT_FOLDER"
    OUTPUT = "OUTPUT"
    OUTPUT_LOG = "OUTPUT_LOG"
    STYLE_FOLDER = "STYLE_FOLDER"

    def name(self):
        """アルゴリズムの内部ID"""
        return "dm_to_geopackage"

    def displayName(self):
        """Processing Toolbox の表示名"""
        return "DMファイルをGeoPackageに変換"

    def group(self):
        return ""

    def groupId(self):
        return ""

    def shortHelpString(self):
        """ダイアログ右側に表示されるヘルプ文"""
        return (
            "DMファイルをGeoPackageに変換します。どちらか一方を指定してください。スタイルフォルダを指定すると、変換後にQMLスタイルを自動適用します。\n"
            "単一ファイル処理：DMファイルを指定\n"
            "複数ファイル処理：フォルダを指定\n\n"
        )

    def createInstance(self):
        """QGISが内部でアルゴリズムの複製を作るために使うメソッド"""
        return DmToGeoPackageAlgorithm()

    def initAlgorithm(self, config=None):
        """Processing ダイアログの入力・出力パラメータの定義"""
        # 入力: DMファイル選択
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_FILES,
                "入力：DMファイル",
                behavior=QgsProcessingParameterFile.File,
                fileFilter="DM Files (*.dm)",
                optional=True,
            )
        )

        # 入力: フォルダ指定
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_FOLDER,
                "入力：DMファイルが格納されたフォルダ",
                behavior=QgsProcessingParameterFile.Folder,
                optional=True,
            )
        )

        # オプション: スタイルフォルダ（QML）
        self.addParameter(
            QgsProcessingParameterFile(
                self.STYLE_FOLDER,
                "入力：スタイルフォルダ（QML）",
                behavior=QgsProcessingParameterFile.Folder,
                optional=True,
            )
        )

        # 出力: GeoPackageファイル
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT,
                "出力：GeoPackage",
                fileFilter="GeoPackage Files (*.gpkg)",
            )
        )

        # オプション: 変換ログ出力
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.OUTPUT_LOG,
                "変換ログを出力する",
                defaultValue=False,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """「実行」ボタンを押したときに走る処理の本体"""
        input_file = self.parameterAsFile(parameters, self.INPUT_FILES, context)
        input_folder = self.parameterAsFile(parameters, self.INPUT_FOLDER, context)
        output_path = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        # ファイルリスト構築
        if input_file:
            dm_files = [input_file]
        elif input_folder:
            dm_files = sorted(glob.glob(os.path.join(input_folder, "*.dm")))
            if not dm_files:
                feedback.reportError("フォルダ内にDMファイルが見つかりません")
                return {self.OUTPUT: output_path}
            feedback.pushInfo(f"{len(dm_files)}件のDMファイルを検出")
        else:
            feedback.reportError("DMファイルまたはフォルダを指定してください")
            return {self.OUTPUT: output_path}

        # 各ファイルを解析（座標系が異なるファイルはスキップ）
        parsed_list = []
        base_coord_system = None
        skipped_files = []

        for dm_file in dm_files:
            feedback.pushInfo(f"読み込み中: {dm_file}")
            classified = classify(read_records(dm_file))
            parsed = parse(classified)

            if base_coord_system is None:
                base_coord_system = parsed.mesh_info.coordinate_system
            elif parsed.mesh_info.coordinate_system != base_coord_system:
                skipped_files.append(
                    f"{os.path.basename(dm_file)}"
                    f"(座標系{parsed.mesh_info.coordinate_system})"
                )
                continue

            feedback.pushInfo(
                f"解析完了: {os.path.basename(dm_file)} "
                f"{len(parsed.groups)}グループ, "
                f"座標系{parsed.mesh_info.coordinate_system}"
            )
            parsed_list.append(parsed)

        if skipped_files:
            feedback.reportError(
                f"座標系が異なるためスキップ（基準: 座標系{base_coord_system}）: "
                f"{', '.join(skipped_files)}"
            )

        if not parsed_list:
            feedback.reportError("変換可能なDMファイルがありません")
            return {self.OUTPUT: output_path}

        # レイヤ作成（複数ファイルの同名レイヤはマージ）
        layers = create_merged_layers(parsed_list)
        feedback.pushInfo(f"レイヤ作成完了: {len(layers)}レイヤ")

        save_to_geopackage(layers, output_path)
        feedback.pushInfo(f"GeoPackage出力完了: {output_path}")

        # レイヤーをプロジェクトに追加
        combined_extent = QgsRectangle()
        for layer in layers:
            gpkg_layer = QgsVectorLayer(
                f"{output_path}|layername={layer.name()}",
                layer.name(),
                "ogr",
            )
            context.addLayerToLoadOnCompletion(
                gpkg_layer.id(),
                QgsProcessingContext.LayerDetails(
                    layer.name(),
                    context.project(),
                    layer.name(),
                ),
            )
            context.temporaryLayerStore().addMapLayer(gpkg_layer)

            layer_extent = gpkg_layer.extent()
            if not layer_extent.isEmpty():
                if combined_extent.isEmpty():
                    combined_extent = QgsRectangle(layer_extent)
                else:
                    combined_extent.combineExtentWith(layer_extent)

        self._combined_extent = combined_extent
        self._layer_crs = gpkg_layer.crs()

        feedback.pushInfo(f"{len(layers)}レイヤをプロジェクトに追加")

        # 変換統計の収集（全ファイル分を集約）
        stats = self._collect_stats_multi(parsed_list)

        # 未変換コードがあれば常に処理パネルに警告表示
        self._warn_unconverted(stats, feedback)

        # ログ出力
        output_log = self.parameterAsBool(parameters, self.OUTPUT_LOG, context)
        if output_log:
            first_file = dm_files[0]
            self._write_log(first_file, output_path, parsed_list[0], layers, stats, feedback)

        return {self.OUTPUT: output_path}

    def postProcessAlgorithm(self, context, feedback):
        """レイヤ読み込み後にマップキャンバスを全体表示にズームする。"""
        from qgis.utils import iface

        if iface is None or not hasattr(self, "_combined_extent"):
            return {}
        if self._combined_extent.isEmpty():
            return {}

        canvas = iface.mapCanvas()
        dest_crs = canvas.mapSettings().destinationCrs()
        if dest_crs != self._layer_crs:
            transform = QgsCoordinateTransform(
                self._layer_crs, dest_crs, context.project()
            )
            extent = transform.transformBoundingBox(self._combined_extent)
        else:
            extent = QgsRectangle(self._combined_extent)

        extent.scale(1.05)
        canvas.setExtent(extent)
        canvas.refresh()
        return {}

    def _collect_stats_multi(self, parsed_list):
        """複数ParsedDMから変換統計を収集する。

        Returns:
            dict with keys:
                code_counter: Counter of (element_type, dm_code) → count
                no_coords_count: int
                type_counter: Counter of element_type → count
        """
        code_counter = Counter()
        type_counter = Counter()
        no_coords_count = 0
        for parsed in parsed_list:
            for group in parsed.groups:
                for elem in group.elements:
                    code_counter[(elem.element_type, elem.dm_code)] += 1
                    type_counter[elem.element_type] += 1
                    if not elem.coordinates:
                        no_coords_count += 1
        return {
            "code_counter": code_counter,
            "type_counter": type_counter,
            "no_coords_count": no_coords_count,
        }

    def _warn_unconverted(self, stats, feedback):
        """未変換コードがあれば処理パネルに警告を表示する。"""
        code_counter = stats["code_counter"]
        type_counter = stats["type_counter"]

        # 未対応の要素タイプ
        unsupported_types = []
        type_names = {
            "E1": "面", "E2": "線", "E3": "円", "E4": "弧",
            "E5": "点", "E6": "方向", "E7": "注記", "E8": "属性",
        }
        for et in sorted(type_counter.keys()):
            if et not in _SUPPORTED_TYPES:
                name = type_names.get(et, et)
                unsupported_types.append(f"{et}({name}) {type_counter[et]}件")
        if unsupported_types:
            feedback.reportError(
                f"未対応の要素タイプ: {', '.join(unsupported_types)}"
            )

        # 未定義の分類コード（対応済み要素タイプだがコード表にない）
        undefined_codes = []
        for (et, dm_code), count in sorted(code_counter.items()):
            if et not in _SUPPORTED_TYPES:
                continue
            name = get_classification_name(dm_code)
            if name == dm_code:
                undefined_codes.append(f"{dm_code} {count}件")
        if undefined_codes:
            feedback.reportError(
                f"コード表に未定義の分類コード: {', '.join(undefined_codes)}"
            )

    def _write_log(self, input_file, output_path, parsed, layers, stats, feedback):
        """変換結果のサマリーをテキストファイルに出力する。"""
        input_name = os.path.splitext(os.path.basename(input_file))[0]
        log_path = os.path.join(
            os.path.dirname(output_path), f"{input_name}_log.txt"
        )

        code_counter = stats["code_counter"]
        type_counter = stats["type_counter"]
        no_coords_count = stats["no_coords_count"]

        total = sum(type_counter.values())
        converted = sum(
            count for et, count in type_counter.items() if et in _SUPPORTED_TYPES
        )

        lines = [
            "=== DM変換ログ ===",
            f"入力: {os.path.basename(input_file)}",
            f"座標系: {parsed.index.coordinate_system} (EPSG:{6668 + parsed.index.coordinate_system})",
            f"図郭名: {parsed.index.map_name}",
            f"地図情報レベル: {parsed.index.scale}",
            "",
            "--- 要素タイプ別 ---",
        ]

        type_names = {
            "E1": "面", "E2": "線", "E3": "円", "E4": "弧",
            "E5": "点", "E6": "方向", "E7": "注記", "E8": "属性",
        }
        for et in sorted(type_counter.keys()):
            count = type_counter[et]
            name = type_names.get(et, et)
            status = "✓ 変換済み" if et in _SUPPORTED_TYPES else "✗ 未対応"
            lines.append(f"  {et}({name}): {count}件  {status}")

        lines.extend([
            "",
            f"合計: {total}件 (変換: {converted}件, 未対応: {total - converted}件)",
            f"座標なしスキップ: {no_coords_count}件",
            f"出力レイヤ数: {len(layers)}",
        ])

        # 分類コード別変換実績
        converted_codes = []
        undefined_codes = []
        unsupported_codes = []
        for (et, dm_code), count in sorted(code_counter.items()):
            name = get_classification_name(dm_code)
            if et not in _SUPPORTED_TYPES:
                type_name = type_names.get(et, et)
                unsupported_codes.append(
                    f"  {et} {dm_code}({name}): {count}件（要素タイプ{et}({type_name})は未対応）"
                )
            elif name == dm_code:
                undefined_codes.append(
                    f"  {et} {dm_code}: {count}件（コード表に未定義）"
                )
            else:
                converted_codes.append(f"  {et} {dm_code}({name}): {count}件")

        lines.extend(["", "--- 分類コード別変換実績 ---"])
        if converted_codes:
            lines.extend(converted_codes)
        else:
            lines.append("  (なし)")

        if undefined_codes or unsupported_codes:
            lines.extend(["", "--- 未変換の分類コード ---"])
            lines.extend(undefined_codes)
            lines.extend(unsupported_codes)

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        feedback.pushInfo(f"変換ログ出力: {log_path}")
