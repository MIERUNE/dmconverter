"""QgsProcessingAlgorithm: レイヤにスタイルを適用するアルゴリズム"""

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterFile,
)


class ApplyStyleAlgorithm(QgsProcessingAlgorithm):
    INPUT_GPKG = "INPUT_GPKG"
    STYLE_FILE = "STYLE_FILE"

    def name(self):
        return "apply_style"

    def displayName(self):
        return "スタイルを適用"

    def group(self):
        return ""

    def groupId(self):
        return ""

    def shortHelpString(self):
        return "GeoPackageにQMLスタイルファイルを適用します。"

    def createInstance(self):
        return ApplyStyleAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_GPKG,
                "対象のGeoPackage",
                behavior=QgsProcessingParameterFile.File,
                fileFilter="GeoPackage Files (*.gpkg)",
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                self.STYLE_FILE,
                "QMLスタイルファイル",
                behavior=QgsProcessingParameterFile.File,
                fileFilter="QML Files (*.qml)",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """TODO: スタイル適用処理を実装する"""
        feedback.pushInfo("スタイル適用処理は未実装です")
        return {}
