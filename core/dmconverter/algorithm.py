"""QgsProcessingAlgorithm: DM→GeoPackage変換アルゴリズム

入力: DMファイル選択 or フォルダ指定
出力: GeoPackageファイル
"""

import glob
import os
from collections import Counter

from qgis.core import (
    QgsCoordinateTransform,
    QgsLayerTreeGroup,
    QgsProcessingAlgorithm,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
)

from .constants import CLASSIFICATIONS, get_classification_name
from .parser.classifier import classify
from .parser.parser import parse
from .parser.reader import read_records
from .writer.log_writer import write_log
from .writer.writer import create_merged_layers, save_to_geopackage

# 現在変換対応している要素タイプ
_SUPPORTED_TYPES = {"E1", "E2", "E5", "E7"}


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

        # オプション: 変換ログ出力
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.OUTPUT_LOG,
                "変換ログを出力する",
                defaultValue=False,
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
        base_scale = None
        skipped_files = []

        for dm_file in dm_files:
            feedback.pushInfo(f"読み込み中: {dm_file}")
            classified = classify(read_records(dm_file))
            parsed = parse(classified)

            if base_coord_system is None:
                base_coord_system = parsed.mesh_info.coordinate_system
                base_scale = parsed.mesh_info.scale
            elif parsed.mesh_info.coordinate_system != base_coord_system:
                skipped_files.append(
                    f"{os.path.basename(dm_file)}"
                    f"(座標系{parsed.mesh_info.coordinate_system})"
                )
                feedback.reportError(
                    f"座標系が異なるためスキップ（基準: 座標系{base_coord_system}）: "
                    f"{os.path.basename(dm_file)}"
                )
                continue
            elif parsed.mesh_info.scale != base_scale:
                skipped_files.append(
                    f"{os.path.basename(dm_file)}"
                    f"(地図情報レベル{parsed.mesh_info.scale})"
                )
                feedback.reportError(
                    f"地図情報レベルが異なるためスキップ（基準: {base_scale}）: "
                    f"{os.path.basename(dm_file)}"
                )
                continue

            feedback.pushInfo(
                f"解析完了: {os.path.basename(dm_file)} "
                f"{len(parsed.groups)}グループ, "
                f"座標系{parsed.mesh_info.coordinate_system}"
            )
            parsed_list.append(parsed)

        if not parsed_list:
            feedback.reportError("変換可能なDMファイルがありません")
            return {self.OUTPUT: output_path}

        # レイヤ作成（複数ファイルの同名レイヤはマージ）
        merge_result = create_merged_layers(parsed_list)
        layers = merge_result.layers
        if not layers:
            feedback.reportError("変換対象の要素がありません")
            return {self.OUTPUT: output_path}
        feedback.pushInfo(f"レイヤ作成完了: {len(layers)}レイヤ")

        if merge_result.errors:
            for err in merge_result.errors:
                feedback.reportError(f"ジオメトリ変換エラー: {err}")

        write_errors = save_to_geopackage(layers, output_path)
        if write_errors:
            for err in write_errors:
                feedback.reportError(f"GeoPackage書き出し失敗: {err}")
            return {self.OUTPUT: output_path}
        feedback.pushInfo(f"GeoPackage出力完了: {output_path}")

        # パスとレイヤ名を保存
        self._output_path = output_path
        self._layer_names = [layer.name() for layer in layers]
        self._layer_parent_codes = merge_result.layer_parent_codes

        feedback.pushInfo(f"{len(layers)}レイヤをプロジェクトに追加します")

        # 変換統計の収集（全ファイル分を集約）
        stats = self._collect_stats(parsed_list)

        # 未変換コードがあれば常に処理パネルに警告表示
        self._warn_unconverted(stats, feedback)

        # ログ出力
        output_log = self.parameterAsBool(parameters, self.OUTPUT_LOG, context)
        if output_log:
            log_path = write_log(
                dm_files,
                parsed_list[0],
                layers,
                stats,
                _SUPPORTED_TYPES,
                merge_result.geom_fail_counter,
                merge_result.errors,
                skipped_files,
            )
            feedback.pushInfo(f"変換ログ出力: {log_path}")

        return {self.OUTPUT: output_path}

    def postProcessAlgorithm(self, context, feedback):
        """レイヤをプロジェクトに追加し、マップキャンバスを全体表示にズームする。"""
        from qgis.utils import iface

        if not hasattr(self, "_output_path") or not hasattr(self, "_layer_names"):
            return {}

        project = QgsProject.instance()
        combined_extent = QgsRectangle()
        layer_crs = None

        root = project.layerTreeRoot()
        dm_group = root.findGroup("DM") or root.insertGroup(0, "DM")
        sub_groups: dict[str, QgsLayerTreeGroup] = {}

        for name in self._layer_names:
            uri = f"{self._output_path}|layername={name}"
            gpkg_layer = QgsVectorLayer(uri, name, "ogr")

            if not gpkg_layer.isValid():
                feedback.pushWarning(f"レイヤ無効: {name}")
                continue

            parent_code = self._layer_parent_codes.get(name, "")
            group_name = CLASSIFICATIONS.get(parent_code, {}).get("name", parent_code)
            if group_name not in sub_groups:
                sub_groups[group_name] = dm_group.findGroup(group_name) or dm_group.addGroup(group_name)

            project.addMapLayer(gpkg_layer, False)
            sub_groups[group_name].addLayer(gpkg_layer)
            layer_crs = gpkg_layer.crs()

            layer_extent = gpkg_layer.extent()
            if not layer_extent.isEmpty():
                if combined_extent.isEmpty():
                    combined_extent = QgsRectangle(layer_extent)
                else:
                    combined_extent.combineExtentWith(layer_extent)

        # ズーム処理
        if iface is None or combined_extent.isEmpty() or layer_crs is None:
            return {}

        canvas = iface.mapCanvas()
        dest_crs = canvas.mapSettings().destinationCrs()
        if dest_crs != layer_crs:
            transform = QgsCoordinateTransform(layer_crs, dest_crs, context.project())
            extent = transform.transformBoundingBox(combined_extent)
        else:
            extent = QgsRectangle(combined_extent)

        extent.scale(1.05)
        canvas.setExtent(extent)
        canvas.refresh()
        return {}

    def _collect_stats(self, parsed_list):
        """複数ParsedDMから変換統計を収集する。

        Returns:
            以下のキーを持つ辞書を返す:
                code_counter: Counter of (element_type, dm_code) → count
                type_counter: Counter of element_type → count
                no_coords_counter: Counter of (element_type, dm_code) → count
        """
        code_counter = Counter()
        type_counter = Counter()
        no_coords_counter = Counter()
        for parsed in parsed_list:
            for group in parsed.groups:
                for elem in group.elements:
                    code_counter[(elem.element_type, elem.dm_code)] += 1
                    type_counter[elem.element_type] += 1
                    if not elem.coordinates:
                        no_coords_counter[(elem.element_type, elem.dm_code)] += 1
        return {
            "code_counter": code_counter,
            "type_counter": type_counter,
            "no_coords_counter": no_coords_counter,
        }

    def _warn_unconverted(self, stats, feedback):
        """未対応の要素タイプ・未定義コードを警告表示する。"""
        type_counter = stats["type_counter"]
        code_counter = stats["code_counter"]

        type_names = {
            "E1": "面",
            "E2": "線",
            "E3": "円",
            "E4": "弧",
            "E5": "点",
            "E6": "方向",
            "E7": "注記",
            "E8": "属性",
        }

        unsupported = []
        for et in sorted(type_counter.keys()):
            if et not in _SUPPORTED_TYPES:
                name = type_names.get(et, et)
                unsupported.append(f"{et}({name}) {type_counter[et]}件")
        if unsupported:
            feedback.reportError(f"未対応の要素タイプ: {', '.join(unsupported)}")

        undefined = []
        for (et, dm_code), count in sorted(code_counter.items()):
            if et not in _SUPPORTED_TYPES:
                continue
            name = get_classification_name(dm_code)
            if name == dm_code:
                undefined.append(f"{dm_code} {count}件")
        if undefined:
            feedback.reportError(
                f"コード表に未定義の分類コード: {', '.join(undefined)}"
            )
