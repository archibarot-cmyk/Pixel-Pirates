"""
Pixel Pirates NDVI Assistant - Dock Widget
--------------------------------------------
The sidebar UI: a text query box, a Run button, a status/plan panel,
and two stat labels. Emits runRequested(str) with the query text
whenever the user clicks Run.
"""

import os

from qgis.PyQt import uic
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import QDockWidget

# Load the .ui file created in Qt Designer, sitting next to this file.
FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "dockwidget_base.ui")
)


class PixelPiratesDockWidget(QDockWidget, FORM_CLASS):

    # Emitted with the query text when the user clicks "Run".
    runRequested = pyqtSignal(str)

    # Emitted when the dock widget is closed, so the main plugin can
    # forget its reference and recreate it fresh next time.
    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(PixelPiratesDockWidget, self).__init__(parent)
        # Build the UI defined in dockwidget_base.ui onto this widget.
        self.setupUi(self)

        # Wire the Run button to emit our custom signal.
        self.runButton.clicked.connect(self._on_run_clicked)

        # Sensible starting state.
        self.statusTextEdit.setReadOnly(True)
        self.set_status("Type a question and click Run.")
        self.set_stats("--", "--")

    def _on_run_clicked(self):
        """Read the query box and emit runRequested if it isn't empty."""
        query_text = self.queryLineEdit.text().strip()
        if query_text:
            self.runRequested.emit(query_text)

    def set_status(self, message: str):
        """Show a status / parsed-plan message in the read-only text area."""
        self.statusTextEdit.setPlainText(message)

    def set_stats(self, value_label: str, change_label: str):
        """Update the two stat labels (e.g. 'Area lost' and '% change')."""
        self.valueStatLabel.setText(str(value_label))
        self.changeStatLabel.setText(str(change_label))

    def closeEvent(self, event):
        """Let the main plugin know this dock widget is closing."""
        self.closingPlugin.emit()
        event.accept()
