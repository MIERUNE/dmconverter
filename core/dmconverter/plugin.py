import contextlib
import os

from qgis.core import QgsApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QToolButton

from .provider import DmConverterProvider

with contextlib.suppress(ImportError):
    from processing import execAlgorithmDialog


class Plugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.tool_button_action = None

    def initGui(self):
        self.provider = DmConverterProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

        if self.iface:
            self._setup_tool_button()

    def unload(self):
        if self.tool_button_action is not None:
            self.iface.removeToolBarIcon(self.tool_button_action)
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)

    def _setup_tool_button(self):
        icon_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "imgs", "icon.png"
        )
        tool_button = QToolButton()
        action = QAction(
            QIcon(icon_path), "DMファイルをGeoPackageに変換", self.iface.mainWindow()
        )
        action.triggered.connect(
            lambda: execAlgorithmDialog("dmconverter:dm_to_geopackage", {})
        )
        tool_button.setDefaultAction(action)
        self.tool_button_action = self.iface.addToolBarWidget(tool_button)
