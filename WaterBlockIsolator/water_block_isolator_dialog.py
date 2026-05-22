import os
from qgis.PyQt import uic
from qgis.PyQt import QtWidgets

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'water_block_isolator_dialog_base.ui'))


class WaterBlockIsolatorDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(WaterBlockIsolatorDialog, self).__init__(parent)
        self.setupUi(self)
