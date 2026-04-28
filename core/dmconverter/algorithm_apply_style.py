"""QgsProcessingAlgorithm: 既存GeoPackageにスタイルを適用してQLRを出力するアルゴリズム"""

from __future__ import annotations

import glob
import os

from qgis.core import (
    QgsLayerTreeGroup,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProviderRegistry,
    QgsVectorLayer,
)

from .writer.style import (
    apply_qml_by_geom_type,
    build_qml_map,
    build_renderer_cache,
    export_qlr,
)


class ApplyStyleAlgorithm(QgsProcessingAlgorithm):
    INPUT_GPKG = "INPUT_GPKG"
    INPUT_FOLDER = "INPUT_FOLDER"
    STYLE_FOLDER = "STYLE_FOLDER"
    OUTPUT_QLR = "OUTPUT_QLR"

    def name(self):
        return "apply_style"

    def displayName(self):
        return "スタイルを適用してQLRを出力"

    def group(self):
        return ""

    def groupId(self):
        return ""

    def shortHelpString(self):
        return (
            "GeoPackageにQMLスタイルを適用してQLRファイルを出力します。\n"
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
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_QLR,
                "出力：QLRファイル（単一ファイルモードのみ）",
                fileFilter="QGIS Layer Definition Files (*.qlr)",
                optional=True,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        input_gpkg = self.parameterAsFile(parameters, self.INPUT_GPKG, context)
        input_folder = self.parameterAsFile(parameters, self.INPUT_FOLDER, context)
        style_folder = self.parameterAsFile(parameters, self.STYLE_FOLDER, context)

        if not style_folder:
            feedback.reportError("スタイルフォルダを指定してください")
            return {}

        qml_map = build_qml_map(style_folder, feedback)
        if not qml_map:
            feedback.reportError(
                "スタイルフォルダ内に有効なQMLファイルが見つかりません"
            )
            return {}
        feedback.pushInfo(
            f"QMLマップ構築完了: {len(qml_map)}種のジオメトリタイプに対応"
        )
        renderer_cache = build_renderer_cache(qml_map, feedback)

        if input_gpkg:
            gpkg_files = [input_gpkg]
        elif input_folder:
            gpkg_files = sorted(glob.glob(os.path.join(input_folder, "*.gpkg")))
            if not gpkg_files:
                feedback.reportError("フォルダ内にGeoPackageファイルが見つかりません")
                return {}
            feedback.pushInfo(f"{len(gpkg_files)}件のGeoPackageファイルを検出")
        else:
            feedback.reportError("GeoPackageファイルまたはフォルダを指定してください")
            return {}

        output_qlr = ""
        for gpkg_path in gpkg_files:
            feedback.pushInfo(f"処理中: {gpkg_path}")
            qlr_path = self._process_gpkg(gpkg_path, renderer_cache, feedback)
            if qlr_path:
                output_qlr = qlr_path

        if not input_gpkg:
            return {}

        if output_qlr:
            specified = self.parameterAsFileOutput(parameters, self.OUTPUT_QLR, context)
            if specified and os.path.exists(output_qlr):
                os.replace(output_qlr, specified)
                output_qlr = specified

        return {self.OUTPUT_QLR: output_qlr} if output_qlr else {}

    def _process_gpkg(
        self, gpkg_path: str, renderer_cache: dict, feedback
    ) -> str | None:
        """1つのGeoPackageにスタイルを適用してQLRを出力する。

        Returns:
            出力したQLRのパス。失敗した場合はNone。
        """
        sublayers = QgsProviderRegistry.instance().querySublayers(gpkg_path)
        if not sublayers:
            feedback.pushWarning(f"レイヤが見つかりません: {gpkg_path}")
            return None

        temp_group = QgsLayerTreeGroup()
        for sublayer in sublayers:
            layer_name = sublayer.name()
            uri = f"{gpkg_path}|layername={layer_name}"
            layer = QgsVectorLayer(uri, layer_name, "ogr")

            if not layer.isValid():
                feedback.pushWarning(f"レイヤ無効: {layer_name}")
                continue

            apply_qml_by_geom_type(layer, renderer_cache)
            temp_group.addLayer(layer)

        nodes = temp_group.children()
        if not nodes:
            feedback.reportError(f"有効なレイヤがありません: {gpkg_path}")
            return None

        qlr_path = os.path.splitext(gpkg_path)[0] + ".qlr"
        err = export_qlr(nodes, qlr_path)
        if err:
            feedback.reportError(f"QLRエクスポート失敗: {err}")
            return None

        feedback.pushInfo(f"QLR出力完了: {qlr_path}")
        return qlr_path
