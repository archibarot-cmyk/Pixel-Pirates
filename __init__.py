"""
Pixel Pirates NDVI Assistant
-----------------------------
QGIS plugin entry point. QGIS calls classFactory(iface) when the plugin
is loaded, handing it a reference to the running QGIS application so the
plugin can add toolbar buttons, open dock widgets, add map layers, etc.
"""


def classFactory(iface):
    """Load PixelPiratesPlugin class from file main_plugin.py.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .main_plugin import PixelPiratesPlugin
    return PixelPiratesPlugin(iface)
