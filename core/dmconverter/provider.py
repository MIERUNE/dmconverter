"""QgsProcessingProvider: DM変換アルゴリズムをProcessing Toolboxに登録する"""

import os

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .algorithm import DmToGeoPackageAlgorithm


class DmConverterProvider(QgsProcessingProvider):
    def id(self):
        return "dmconverter"

    def name(self):
        return "DM Converter"

    def icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), '..', '..', 'imgs', 'icon.png')
        return QIcon(icon_path)

    def loadAlgorithms(self):
        self.addAlgorithm(DmToGeoPackageAlgorithm())
