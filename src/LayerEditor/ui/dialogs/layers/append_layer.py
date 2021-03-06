"""
Dialog for appending new layer to the end.
"""

import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui as QtGui
from .layers_helpers import LayersHelpers
from LayerEditor.leconfig import cfg
import gm_base.icon as icon

class AppendLayerDlg(QtWidgets.QDialog):

    def __init__(self, parent, min_elevation=None, max_elevation=None, prepend=False, add=False):
        super(AppendLayerDlg, self).__init__(parent)
        if add:
            self.setWindowTitle("Add Layer to Shadow Block")
        elif prepend:
            self.setWindowTitle("Prepend Layer")
        else:
            self.setWindowTitle("Append Layer")
        grid = QtWidgets.QGridLayout(self)

        d_layer_name = QtWidgets.QLabel("Layer Name:", self)
        self.layer_name = QtWidgets.QLineEdit()
        self.have_default_name = True
        self.set_default_name()
        self.layer_name.textChanged.connect(self.lay_name_changed)

        self.image = QtWidgets.QLabel(self)
        self.image.setMinimumWidth(self.layer_name.sizeHint().height())
        self.image.setPixmap(icon.get_app_icon("sign-check").pixmap(self.layer_name.sizeHint().height()))
        self.image.setToolTip('Layer name is unique, everything is fine.')

        grid.addWidget(d_layer_name, 0, 0)
        grid.addWidget(self.layer_name, 0, 1)
        grid.addWidget(self.image, 0, 2)
        
        d_surface = QtWidgets.QLabel("Bottom Interface Surface:", self)
        grid.addWidget(d_surface, 1, 0)
        i = LayersHelpers.add_surface_to_grid(self, grid, 2)
        
        self.validator = QtGui.QDoubleValidator()
        if add:
            self.validator.setBottom(min_elevation)
            self.validator.setTop(max_elevation)
            self.elevation.setText(str((min_elevation + max_elevation) / 2))
        elif prepend:
            self.validator.setBottom(min_elevation)
            self.elevation.setText(str(min_elevation + 100))
        else:
            self.validator.setTop(max_elevation)
            self.elevation.setText(str(max_elevation - 100))
        self.elevation.setValidator(self.validator)
        
        if add:
            self._tranform_button = QtWidgets.QPushButton("Add", self)
        elif prepend:
            self._tranform_button = QtWidgets.QPushButton("Prepend", self)
        else:
            self._tranform_button = QtWidgets.QPushButton("Append", self)
        self._tranform_button.clicked.connect(self.accept)
        self._cancel_button = QtWidgets.QPushButton("Cancel", self)
        self._cancel_button.clicked.connect(self.reject)

        button_box = QtWidgets.QDialogButtonBox()
        button_box.addButton(self._tranform_button, QtWidgets.QDialogButtonBox.AcceptRole)
        button_box.addButton(self._cancel_button, QtWidgets.QDialogButtonBox.RejectRole)

        grid.addWidget(button_box, i, 3, 1, 3)
        self.setLayout(grid)

    @classmethod
    def is_unique_layer_name(self, lay_name):
        """ Return False in the case of colision with an existing region name."""
        for _, layer in cfg.diagram.regions.layers.items():
            if lay_name == layer:
                return False
        return True

    def lay_name_changed(self, name):
        """ Called when Region Line Edit is changed."""
        self.have_default_name = False
        if self.is_unique_layer_name(name):
            self.image.setPixmap(
                icon.get_app_icon("sign-check").pixmap(self.layer_name.sizeHint().height())
            )
            self.image.setToolTip('Unique name is OK.')
            self._tranform_button.setEnabled(True)
        else:
            self.image.setPixmap(
                icon.get_app_icon("warning").pixmap(self.layer_name.sizeHint().height())
            )
            self.image.setToolTip('Name is not unique!')
            self._tranform_button.setEnabled(False)

    def set_default_name(self):
        """ Set default name if it seems to be default name. """
        if self.have_default_name:
            lay_id = 0
            name = cfg.diagram.regions.layers[0]
            while not self.is_unique_layer_name(name):
                lay_id += 1
                name = "Layer_" + str(lay_id)
            self.layer_name.setText(name)
            self.have_default_name = True

    def accept(self):
        """
        Accepts the form if elevation data fields are valid.
        :return: None
        """
        if LayersHelpers.validate_depth(self.elevation, self.validator, self):
            super(AppendLayerDlg, self).accept()
            
    def fill_surface(self, interface):
        """Fill set surface"""
        return LayersHelpers.fill_surface(self, interface)
