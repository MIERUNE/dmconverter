"""QgsProcessingAlgorithm: レイヤにスタイルを適用するアルゴリズム"""

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterFile,
)


class ApplyStyleAlgorithm(QgsProcessingAlgorithm):
    INPUT_GPKG = "INPUT_GPKG"
    INPUT_FOLDER = "INPUT_FOLDER"
    STYLE_FOLDER = "STYLE_FOLDER"

    def name(self):
        return "apply_style"

    def displayName(self):
        return "スタイルを適用"

    def group(self):
        return ""

    def groupId(self):
        return ""

    def shortHelpString(self):
        return (
            "GeoPackageにQMLスタイルフォルダを適用します。どちらか一方を指定してください。\n"
            "単一ファイル処理：GeoPackageファイルを指定\n"
            "複数ファイル処理：GeoPackageが格納されたフォルダを指定\n"
        )

    def createInstance(self):
        return ApplyStyleAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_GPKG,
                "入力：GeoPackageファイル",
                behavior=QgsProcessingParameterFile.File,
                fileFilter="GeoPackage Files (*.gpkg)",
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_FOLDER,
                "入力：GeoPackageが格納されたフォルダ",
                behavior=QgsProcessingParameterFile.Folder,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                self.STYLE_FOLDER,
                "入力：スタイルフォルダ（QML）",
                behavior=QgsProcessingParameterFile.Folder,
                optional=True,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """TODO: スタイル適用処理を実装する"""
        feedback.pushInfo("スタイル適用処理は未実装です")
        return {}
