"""QgsProcessingAlgorithm: DM→GeoPackage変換アルゴリズム

入力: DMファイル選択 or フォルダ指定
出力: GeoPackageファイル
"""

import os
from collections import Counter

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsVectorLayer,
)

from .classifier import classify
from .parser.parser import parse
from .reader import read_records
from .writer import create_layers, save_to_geopackage

# 現在変換対応している要素タイプ
_SUPPORTED_TYPES = {"E2", "E5"}


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
        output_path = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        if not input_file:
            feedback.reportError("DMファイルを指定してください")
            return {self.OUTPUT: output_path}

        feedback.pushInfo(f"読み込み中: {input_file}")
        classified = classify(read_records(input_file))
        parsed = parse(classified)

        feedback.pushInfo(
            f"解析完了: {len(parsed.groups)}グループ, "
            f"座標系{parsed.mesh_info.coordinate_system}"
        )

        layers = create_layers(parsed)
        feedback.pushInfo(f"レイヤ作成完了: {len(layers)}レイヤ")

        save_to_geopackage(layers, output_path)
        feedback.pushInfo(f"GeoPackage出力完了: {output_path}")

        # レイヤーをプロジェクトに追加
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

        feedback.pushInfo(f"{len(layers)}レイヤをプロジェクトに追加")

        # ログ出力
        output_log = self.parameterAsBool(parameters, self.OUTPUT_LOG, context)
        if output_log:
            self._write_log(input_file, output_path, parsed, layers, feedback)

        return {self.OUTPUT: output_path}

    def _write_log(self, input_file, output_path, parsed, layers, feedback):
        """変換結果のサマリーをテキストファイルに出力する。"""
        input_name = os.path.splitext(os.path.basename(input_file))[0]
        log_path = os.path.join(
            os.path.dirname(output_path), f"{input_name}_log.txt"
        )

        # 要素タイプ別カウント
        type_counter = Counter()
        no_coords_count = 0
        for group in parsed.groups:
            for elem in group.elements:
                type_counter[elem.element_type] += 1
                if not elem.coordinates:
                    no_coords_count += 1

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
            "要素タイプ別:",
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

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        feedback.pushInfo(f"変換ログ出力: {log_path}")
