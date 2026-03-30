"""QgsProcessingAlgorithm: DM→GeoPackage変換アルゴリズム

入力: DMファイル選択 or フォルダ指定
出力: GeoPackageファイル
"""

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
)

from core.dmconverter.classifier import classify
from core.dmconverter.parser.parser import parse
from core.dmconverter.reader import detect_encoding, read_records
from core.dmconverter.writer import create_layers, save_to_geopackage


class DmToGeoPackageAlgorithm(QgsProcessingAlgorithm):
    # パラメータの名前（内部で使うキー）
    INPUT_FILES = "INPUT_FILES"
    INPUT_FOLDER = "INPUT_FOLDER"
    OUTPUT = "OUTPUT"

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
            "DMファイルをGeoPackageに変換します。どちらか一方を指定してください。\n"
            "単一ファイル処理：DMファイルを指定\n"
            "複数ファイル処理：フォルダを指定\n"
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
        encoding = detect_encoding(input_file)
        classified = classify(read_records(input_file))
        parsed = parse(classified, encoding)

        feedback.pushInfo(
            f"解析完了: {len(parsed.groups)}グループ, "
            f"座標系{parsed.index.coordinate_system}"
        )

        layers = create_layers(parsed)
        feedback.pushInfo(f"レイヤ作成完了: {len(layers)}レイヤ")

        save_to_geopackage(layers, output_path)
        feedback.pushInfo(f"GeoPackage出力完了: {output_path}")

        return {self.OUTPUT: output_path}
