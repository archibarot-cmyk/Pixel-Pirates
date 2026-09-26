"""
Pixel Pirates NDVI Assistant - Main Plugin
--------------------------------------------
Registers the plugin with QGIS: adds a toolbar button that opens the
dock widget, and wires the dock widget's runRequested signal to a
placeholder handler. Replace on_run() later with real LLM + engine calls
(see the TODO comments inside on_run).
"""

import os.path

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .dockwidget import PixelPiratesDockWidget


class PixelPiratesPlugin:
    """QGIS Plugin Implementation for Pixel Pirates NDVI Assistant."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this
            class which provides the hook by which you can manipulate
            the QGIS application at run time.
        :type iface: QgsInterface
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        self.actions = []
        self.menu = "&Pixel Pirates NDVI Assistant"
        self.toolbar = self.iface.addToolBar("PixelPiratesNDVIAssistant")
        self.toolbar.setObjectName("PixelPiratesNDVIAssistant")

        self.dock_widget = None

    # ------------------------------------------------------------------
    # GUI setup / teardown
    # ------------------------------------------------------------------

    def initGui(self):
        """Create the menu entry and toolbar icon inside the QGIS GUI."""
        icon_path = os.path.join(self.plugin_dir, "resources", "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        action = QAction(icon, "Pixel Pirates NDVI Assistant", self.iface.mainWindow())
        action.triggered.connect(self.run)
        action.setEnabled(True)

        self.toolbar.addAction(action)
        self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)

    def unload(self):
        """Remove the plugin menu items, icon, and dock widget from QGIS."""
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

        if self.dock_widget is not None:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget = None

    # ------------------------------------------------------------------
    # Core behaviour
    # ------------------------------------------------------------------

    def run(self):
        """Open the dock widget (creating it the first time it's needed)."""
        if self.dock_widget is None:
            self.dock_widget = PixelPiratesDockWidget()
            self.dock_widget.runRequested.connect(self.on_run)
            self.dock_widget.closingPlugin.connect(self._on_dock_closed)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
        self.dock_widget.show()

        def on_run(self, query_text: str):
        """Handle a query submitted from the dock widget: plan -> engine -> map."""
        from llm.llm_client import get_plan
        from llm.validator import PlanValidationError
        from engine.ndvi import compute_ndvi
        from engine.change_detection import change_detection
        from engine.area_extraction import area_extraction
        from qgis.core import (
            QgsRasterLayer,
            QgsProject,
            QgsSingleBandPseudoColorRenderer,
        )

        try:
            plan = get_plan(query_text)

            if plan["operation"] == "reject":
                self.dock_widget.set_status(f"Can't process that: {plan['reason']}")
                return

            self.dock_widget.set_status(f"Running {plan['operation']}...")

            if plan["operation"] == "ndvi":
                output_path, stats = compute_ndvi(plan["year_1"])
            elif plan["operation"] == "change_detection":
                output_path, stats = change_detection(plan["year_1"], plan["year_2"])
            elif plan["operation"] == "area_extraction":
                output_path, stats = area_extraction(plan["year_1"])
            else:
                self.dock_widget.set_status(f"Unknown operation: {plan['operation']}")
                return

            layer_name = f"{plan['operation']}_{plan.get('year_1')}"
            raster_layer = QgsRasterLayer(output_path, layer_name)

            if not raster_layer.isValid():
                self.dock_widget.set_status("Error: output raster failed to load.")
                return

            renderer = QgsSingleBandPseudoColorRenderer(
                raster_layer.dataProvider(), 1
            )
            raster_layer.setRenderer(renderer)
            raster_layer.triggerRepaint()

            QgsProject.instance().addMapLayer(raster_layer)

            self.dock_widget.set_stats(stats)
            self.dock_widget.set_status("Done.")

        except PlanValidationError as e:
            self.dock_widget.set_status(f"Invalid query: {e}")
        except Exception as e:
            self.dock_widget.set_status(f"Error: {e}")
        
    def _on_dock_closed(self):
        """Forget the dock widget reference once the user closes it."""
        self.dock_widget = None
