"""QgsProcessingAlgorithm: DM→GeoPackage変換アルゴリズム

入力: DMファイル選択 or フォルダ指定
出力: GeoPackageファイル
"""

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsVectorLayer,
)

from .classifier import classify
from .parser.parser import parse
from .reader import read_records
from .writer import create_layers, save_to_geopackage


class DmToGeoPackageAlgorithm(QgsProcessingAlgorithm):
    INPUT_FILES = "INPUT_FILES"
    INPUT_FOLDER = "INPUT_FOLDER"
    OUTPUT = "OUTPUT"
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

        return {self.OUTPUT: output_path}
