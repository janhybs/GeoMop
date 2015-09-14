# -*- coding: utf-8 -*-
"""
Ssh preset
@author: Jan Gabriel
@contact: jan.gabriel@tul.cz
"""

from ui.dialogs.dialogs import UiPresetsDialog, AbstractPresetsDialog
from ui.dialogs.ssh_dialog import SshDialog


class SshPresets(AbstractPresetsDialog):
    """
    Dialog executive code with bindings and other functionality.
    """

    def __init__(self, parent=None, presets=None):
        super(SshPresets, self).__init__(parent)

        # setup preset specific UI
        self.ui = UiSshPresets()
        self.ui.setup_ui(self)

        # assign presets and reload view
        self. presets = presets
        self._reload_view(self.presets)

        # set custom dialog
        self.presets_dlg = SshDialog()

        # connect generic presets slots (must be called after UI setup)
        super(SshPresets, self)._connect_slots()


class UiSshPresets(UiPresetsDialog):
    """
    UI extensions of presets dialog.
    """
    def setup_ui(self, dialog):
        super().setup_ui(dialog)

        # dialog properties
        dialog.resize(680, 510)
        dialog.setObjectName("SshPresetsDialog")
        dialog.setWindowTitle("SSH Presets")