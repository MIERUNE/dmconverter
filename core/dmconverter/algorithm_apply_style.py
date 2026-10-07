"""QgsProcessingAlgorithm: 既存GeoPackageにスタイルを適用してQLRを出力するアルゴリズム"""

from __future__ import annotations

import os

from qgis.core import (
    Qgis,
    QgsCoordinateTransform,
    QgsFeatureRequest,
    QgsLayerTreeGroup,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProject,
    QgsProviderRegistry,
    QgsRectangle,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QCoreApplication

from .constants import CLASSIFICATIONS
from .writer.style import (
    apply_annotation_labels,
    apply_direction_rotation,
    apply_kandan_filter,
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
        )

    def createInstance(self):
        return ApplyStyleAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_GPKG,
                "入力：GeoPackageファイル",
                behavior=Qgis.ProcessingFileParameterBehavior.File,
                fileFilter="GeoPackage Files (*.gpkg)",
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                self.STYLE_FOLDER,
                "入力：スタイルフォルダ（QML）",
                behavior=Qgis.ProcessingFileParameterBehavior.Folder,
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_QLR,
                "出力：QLRファイル",
                fileFilter="QGIS Layer Definition Files (*.qlr)",
                optional=True,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        input_gpkg = self.parameterAsFile(parameters, self.INPUT_GPKG, context)
        style_folder = self.parameterAsFile(parameters, self.STYLE_FOLDER, context)

        if not input_gpkg:
            feedback.reportError("GeoPackageファイルを指定してください")
            return {}

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
        feedback.setProgress(5)
        renderer_cache = build_renderer_cache(qml_map, feedback)
        feedback.setProgress(10)

        self._gpkg_files = [input_gpkg]
        self._style_folder = style_folder

        feedback.pushInfo(f"処理中: {input_gpkg}")
        output_qlr = self._process_gpkg(input_gpkg, renderer_cache, feedback) or ""
        feedback.setProgress(70)

        if output_qlr:
            specified = self.parameterAsFileOutput(parameters, self.OUTPUT_QLR, context)
            if specified and os.path.exists(output_qlr):
                os.replace(output_qlr, specified)
                output_qlr = specified

        return {self.OUTPUT_QLR: output_qlr} if output_qlr else {}

    def postProcessAlgorithm(self, context, feedback):
        """レイヤをプロジェクトに追加し、マップキャンバスを全体表示にズームする。"""
        from qgis.utils import iface

        if not hasattr(self, "_gpkg_files") or not hasattr(self, "_style_folder"):
            return {}

        qml_map = build_qml_map(self._style_folder, feedback)
        renderer_cache = build_renderer_cache(qml_map, feedback)

        project = QgsProject.instance()
        root = project.layerTreeRoot()
        combined_extent = QgsRectangle()
        layer_crs = None

        dm_group = root.findGroup("DM") or root.insertGroup(0, "DM")

        all_sublayers = {
            gp: QgsProviderRegistry.instance().querySublayers(gp)
            for gp in self._gpkg_files
        }
        total_layers = sum(len(sl) for sl in all_sublayers.values())
        layer_idx = 0

        for gpkg_path in self._gpkg_files:
            sub_groups: dict[str, QgsLayerTreeGroup] = {}

            sublayers = all_sublayers[gpkg_path]
            for sublayer in sublayers:
                layer_name = sublayer.name()
                uri = f"{gpkg_path}|layername={layer_name}"
                layer = QgsVectorLayer(uri, layer_name, "ogr")
                if not layer.isValid():
                    feedback.pushWarning(f"レイヤ無効: {layer_name}")
                    continue

                # HCODE2フィールドの先頭2文字で分類コードを取得
                # CLASSIFICATIONSにない場合は2文字コードをそのままグループ名に使用
                parent_code = ""
                hcode2_idx = layer.fields().lookupField("HCODE2")
                if hcode2_idx >= 0:
                    feat = next(
                        layer.getFeatures(QgsFeatureRequest().setLimit(1)), None
                    )
                    if feat:
                        parent_code = str(feat.attribute("HCODE2") or "")[:2]

                sg_name = (
                    CLASSIFICATIONS.get(parent_code, {}).get("name", parent_code)
                    or "未分類"
                )
                if sg_name not in sub_groups:
                    sub_groups[sg_name] = dm_group.findGroup(
                        sg_name
                    ) or dm_group.addGroup(sg_name)

                project.addMapLayer(layer, False)
                sub_groups[sg_name].addLayer(layer)

                is_annotation = layer.fields().lookupField("注記内容") >= 0
                if is_annotation:
                    apply_annotation_labels(layer)
                elif renderer_cache:
                    apply_qml_by_geom_type(layer, renderer_cache)
                if layer.fields().lookupField("方向角") >= 0:
                    apply_direction_rotation(layer)
                apply_kandan_filter(layer)

                layer_crs = layer.crs()
                layer_extent = layer.extent()
                if not layer_extent.isEmpty():
                    if combined_extent.isEmpty():
                        combined_extent = QgsRectangle(layer_extent)
                    else:
                        combined_extent.combineExtentWith(layer_extent)

                layer_idx += 1
                if total_layers > 0:
                    feedback.setProgress(70 + int(30 * layer_idx / total_layers))
                if layer_idx % 25 == 0:
                    QCoreApplication.processEvents()

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

        project = QgsProject.instance()
        temp_group = QgsLayerTreeGroup()
        layer_ids: list[str] = []
        for sublayer in sublayers:
            layer_name = sublayer.name()
            uri = f"{gpkg_path}|layername={layer_name}"
            layer = QgsVectorLayer(uri, layer_name, "ogr")

            if not layer.isValid():
                feedback.pushWarning(f"レイヤ無効: {layer_name}")
                continue

            is_annotation = layer.fields().lookupField("注記内容") >= 0
            if is_annotation:
                apply_annotation_labels(layer)
            else:
                apply_qml_by_geom_type(layer, renderer_cache)
            if layer.fields().lookupField("方向角") >= 0:
                apply_direction_rotation(layer)
            apply_kandan_filter(layer)
            # QLRエクスポートにはプロジェクト登録が必要
            project.addMapLayer(layer, False)
            layer_ids.append(layer.id())
            temp_group.addLayer(layer)

        nodes = temp_group.children()
        if not nodes:
            feedback.reportError(f"有効なレイヤがありません: {gpkg_path}")
            project.removeMapLayers(layer_ids)
            return None

        qlr_path = os.path.splitext(gpkg_path)[0] + ".qlr"
        err = export_qlr(nodes, qlr_path, base_path=os.path.dirname(qlr_path))
        project.removeMapLayers(layer_ids)
        if err:
            feedback.reportError(f"QLRエクスポート失敗: {err}")
            return None

        feedback.pushInfo(f"QLR出力完了: {qlr_path}")
        return qlr_path
