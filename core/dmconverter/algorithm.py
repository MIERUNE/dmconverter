"""QgsProcessingAlgorithm: DM→GeoPackage変換アルゴリズム

入力: 複数DMファイル選択 or フォルダ指定（両対応）
出力: GeoPackageファイル
"""

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
)


class DmToGeoPackageAlgorithm(QgsProcessingAlgorithm):
    # パラメータの名前（内部で使うキー）
    INPUT_FILES = "INPUT_FILES"
    INPUT_FOLDER = "INPUT_FOLDER"
    OUTPUT = "OUTPUT"

    def name(self):
        """アルゴリズムの内部ID（英語、小文字）"""
        return "dm_to_geopackage"

    def displayName(self):
        """Processing Toolbox に表示される名前"""
        return "DMファイルをGeoPackageに変換"

    def group(self):
        return ""

    def groupId(self):
        return ""

    def shortHelpString(self):
        """ダイアログ右側に表示されるヘルプ文"""
        return "DMファイルをGeoPackageに変換します。複数ファイルまたはフォルダを指定できます。"

    def createInstance(self):
        """QGISが内部でアルゴリズムの複製を作るために使う（お決まりの書き方）"""
        return DmToGeoPackageAlgorithm()

    def initAlgorithm(self, config=None):
        """入力・出力パラメータの定義

        ここで定義した内容が Processing ダイアログの入力欄になる。
        """
        # 入力: DMファイル選択（任意）
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_FILES,
                "DMファイル",
                behavior=QgsProcessingParameterFile.File,
                fileFilter="DM Files (*.dm)",
                optional=True,
            )
        )

        # 入力: フォルダ指定（任意）
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_FOLDER,
                "DMファイルが格納されたフォルダ",
                behavior=QgsProcessingParameterFile.Folder,
                optional=True,
            )
        )

        # 出力: GeoPackageファイル
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT,
                "出力GeoPackage",
                fileFilter="GeoPackage Files (*.gpkg)",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """「実行」ボタンを押したときに走る処理の本体

        TODO: core/ の実装後にここから変換処理を呼び出す
        """
        output_path = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        feedback.pushInfo("DM変換処理は未実装です")

        return {self.OUTPUT: output_path}
