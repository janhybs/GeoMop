# -*- coding: utf-8 -*-
"""
Multijob dialog
@author: Jan Gabriel
@contact: jan.gabriel@tul.cz
"""

import logging

from PyQt5 import QtCore, QtWidgets, QtGui
from ui.data.mj_data import MultiJobPreset
from ui.dialogs.dialogs import UiFormDialog, AFormDialog
from gm_base.geomop_analysis import Analysis, InvalidAnalysis
from ui.validators.validation import PresetsValidationColorizer


class MultiJobDialog(AFormDialog):
    """
    Dialog executive code with bindings and other functionality.
    """

    # purposes of dialog by action
    PURPOSE_ADD = dict(purposeType="PURPOSE_ADD",
                       objectName="AddMultiJobDialog",
                       windowTitle="Job Panel - Add MultiJob",
                       title="Add MultiJob",
                       subtitle="Please select details to schedule set of "
                                "tasks for computation and press Run to "
                                 "start multijob.")

    PURPOSE_COPY = dict(purposeType="PURPOSE_COPY",
                        objectName="CopyMultiJobDialog",
                        windowTitle="Job Panel - Copy MultiJob",
                        title="Copy MultiJob",
                        subtitle="Change desired parameters and press Run to "
                                 "start multijob.")

    PURPOSE_COPY_PREFIX = "Copy_of"

    def __init__(self, parent=None, data=None):
        super().__init__(parent)

        self.excluded = {"name": []}
        self.permitted = {}

        # setup specific UI
        self.ui = UiMultiJobDialog()
        self.ui.setup_ui(self)
        #self.ui.validator.connect(self.valid)
        self.data = data

        self._from_mj = None

        self.preset = None
        self.pbs = {}
        self.ssh = {}

        # preset purpose
        self.set_purpose(self.PURPOSE_ADD)
        self.set_analyses(data.workspaces)
        self.set_pbs_presets(data.pbs_presets)
        self.set_ssh_presets(data.ssh_presets)

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Save).setText("Run")

        # connect slots
        # connect generic presets slots (must be called after UI setup)
        super()._connect_slots()
        self.ui.analysisComboBox.currentIndexChanged.connect(self.update_mj_name)
        self.ui.multiJobSshPresetComboBox.currentIndexChanged.connect(self._handle_mj_ssh_changed)
        self.ui.jobSshPresetComboBox.currentIndexChanged.connect(self._handle_j_ssh_changed)

    def update_mj_name(self):
        analysis_name = self.ui.analysisComboBox.currentText()
        try:
            counter = Analysis.open(self.data.workspaces.get_path(), analysis_name).mj_counter
        except InvalidAnalysis:
            counter = 1
        name = self.ui.multiJobSshPresetComboBox.currentText() + '_' + str(counter)
        self.ui.nameLineEdit.setText(name)

    def valid(self):
        preset = self.get_data()["preset"]

        # excluded names
        self.excluded["name"] = []
        if self.data.multijobs:
            prefix = preset.analysis + "_"
            prefix_len = len(prefix)
            self.excluded["name"] = [k[prefix_len:] for k in self.data.multijobs.keys() if k.startswith(prefix)]

        errors = preset.validate(self.excluded, self.permitted)
        self.ui.validator.colorize(errors)
        return len(errors)==0

    def _handle_mj_ssh_changed(self, index):
        key = self.ui.multiJobSshPresetComboBox.currentText()
        if key == "" or key == UiMultiJobDialog.SSH_LOCAL_EXEC or self.ssh[key].pbs_system == '':
            self.ui.multiJobPbsPresetComboBox.setEnabled(False)
        else:
            self._enable_pbs(self.ui.multiJobPbsPresetComboBox, key)
        self.update_mj_name()
        self._handle_j_ssh_changed()

    def _enable_pbs(self, combo, key):
        """Enable all pbs presets with same sytems as is in choosed ssh preset"""
        combo.setEnabled(True)
        model = combo.model()
        if not key in self.ssh:
            system = ''
        else:
            system = self.ssh[key].pbs_system
        reselect = False
        curr = combo.currentIndex()
        for i in range(0, combo.count()):
            item = model.item(i)
            if not item.text() in self.pbs:
                continue
            pbs_system = self.pbs[item.text()].pbs_system
            disable = pbs_system is None or system != pbs_system
            if disable:
                item.setFlags(item.flags() & ~(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled))
                item.setData(combo.palette().color(
                    QtGui.QPalette.Disabled, QtGui.QPalette.Text), QtCore.Qt.TextColorRole)
                if curr == i:
                    reselect = True
            else:
                item.setFlags(item.flags() | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled);
                item.setData(QtCore.QVariant(), QtCore.Qt.TextColorRole)
        if reselect:
            combo.setCurrentIndex(0)

    def _handle_j_ssh_changed(self, index=0):
        key = self.ui.jobSshPresetComboBox.currentText()
        if key == UiMultiJobDialog.SSH_LOCAL_EXEC:
            # get server pbs
            key = self.ui.multiJobSshPresetComboBox.currentText()
            if key == '' or key == UiMultiJobDialog.SSH_LOCAL_EXEC or self.ssh[key].pbs_system == '':
                self.ui.jobPbsPresetComboBox.setEnabled(False)
            else:
                self._enable_pbs(self.ui.jobPbsPresetComboBox, key)

        elif key in self.ssh and self.ssh[key].pbs_system == '':
            self.ui.jobPbsPresetComboBox.setEnabled(False)
        else:
            self._enable_pbs(self.ui.jobPbsPresetComboBox, key)

    def set_analyses(self, config):
        self.ui.analysisComboBox.clear()        
        if config is not None:
            path = config.get_path()
            if path is not None:
                for analysis_name in Analysis.list_analyses_in_workspace(path):
                    self.ui.analysisComboBox.addItem(analysis_name, analysis_name)
        if self.ui.analysisComboBox.count()==0:            
            self.ui.analysisComboBox.addItem('')

    def set_pbs_presets(self, pbs):
        self.ui.multiJobPbsPresetComboBox.clear()
        self.ui.jobPbsPresetComboBox.clear()

        # add default PBS options (none)
        self.ui.multiJobPbsPresetComboBox.addItem(self.ui.PBS_OPTION_NONE, self.ui.PBS_OPTION_NONE)
        self.ui.jobPbsPresetComboBox.addItem(self.ui.PBS_OPTION_NONE, self.ui.PBS_OPTION_NONE)

        self.permitted['mj_pbs_preset'] = []
        self.permitted['mj_pbs_preset'].append(None)
        self.permitted['j_pbs_preset'] = []
        self.permitted['j_pbs_preset'].append(None)

        self.pbs = pbs

        if pbs:
            # sort dict by list, not sure how it works
            for key in pbs:
                self.ui.multiJobPbsPresetComboBox.addItem(pbs[key].name, key)
                self.ui.jobPbsPresetComboBox.addItem(pbs[key].name, key)
                self.permitted['mj_pbs_preset'].append(key)
                self.permitted['j_pbs_preset'].append(key)

            self.ui.multiJobPbsPresetComboBox.setCurrentIndex(
                self.ui.multiJobPbsPresetComboBox.findData(
                    'no PBS' if self.preset is None or self.preset.mj_pbs_preset is None else self.preset.mj_pbs_preset))
            self.ui.jobPbsPresetComboBox.setCurrentIndex(
                self.ui.jobPbsPresetComboBox.findData(
                    'no PBS' if self.preset is None or self.preset.j_pbs_preset is None else self.preset.j_pbs_preset))
            self._handle_mj_ssh_changed(0)
            self._handle_j_ssh_changed(0)

    def set_ssh_presets(self, ssh):
        self.ui.multiJobSshPresetComboBox.clear()
        self.ui.jobSshPresetComboBox.clear()

        # add default SSH option for local execution
        self.ui.multiJobSshPresetComboBox.addItem(self.ui.SSH_LOCAL_EXEC, self.ui.SSH_LOCAL_EXEC)
        self.ui.jobSshPresetComboBox.addItem(self.ui.SSH_LOCAL_EXEC, self.ui.SSH_LOCAL_EXEC)

        self.permitted['mj_ssh_preset'] = []
        self.permitted['mj_ssh_preset'].append(None)
        self.permitted['j_ssh_preset'] = []
        self.permitted['j_ssh_preset'].append(None)

        self.ssh = ssh

        if ssh:
            # sort dict by list, not sure how it works
            for key in ssh:
                self.ui.multiJobSshPresetComboBox.addItem(ssh[key].name, key)
                self.ui.jobSshPresetComboBox.addItem(ssh[key].name, key)
                self.permitted['mj_ssh_preset'].append(key)
                self.permitted['j_ssh_preset'].append(key)
            self.ui.multiJobSshPresetComboBox.setCurrentIndex(
                self.ui.multiJobSshPresetComboBox.findData(
                    'local' if self.preset is None or self.preset.mj_ssh_preset is None else self.preset.mj_ssh_preset))
            self.ui.jobSshPresetComboBox.setCurrentIndex(
                self.ui.jobSshPresetComboBox.findData(
                    'local' if self.preset is None or self.preset.j_ssh_preset is None else self.preset.j_ssh_preset))

    def get_data(self):
        key = self.ui.idLineEdit.text()
        preset = MultiJobPreset(name=self.ui.nameLineEdit.text())

        if self.ui.multiJobSshPresetComboBox.currentText() != UiMultiJobDialog.SSH_LOCAL_EXEC:
            if self.ui.multiJobSshPresetComboBox.currentIndex() == -1:
                preset.mj_ssh_preset = ""
            else:
                preset.mj_ssh_preset = self.ui.multiJobSshPresetComboBox.currentData()
        preset.mj_execution_type = UiMultiJobDialog.DELEGATOR_LABEL

        if self.ui.multiJobSshPresetComboBox.currentText() == UiMultiJobDialog.SSH_LOCAL_EXEC:
            preset.mj_execution_type = UiMultiJobDialog.EXEC_LABEL
        elif self.ui.multiJobPbsPresetComboBox.currentText() == UiMultiJobDialog.PBS_OPTION_NONE:
            preset.mj_remote_execution_type = UiMultiJobDialog.EXEC_LABEL
        else:
            preset.mj_remote_execution_type = UiMultiJobDialog.PBS_LABEL
        if self.ui.multiJobPbsPresetComboBox.isEnabled() and \
                self.ui.multiJobPbsPresetComboBox.currentIndex() != 0:
            if self.ui.jobPbsPresetComboBox.currentIndex() == -1:
                preset.mj_pbs_preset = ""
            else:
                preset.mj_pbs_preset =\
                    self.ui.multiJobPbsPresetComboBox.currentData()
            if preset.mj_pbs_preset is None:
                preset.mj_pbs_preset = ""

        if self.ui.jobSshPresetComboBox.currentText() != UiMultiJobDialog.SSH_LOCAL_EXEC:
            if self.ui.jobSshPresetComboBox.currentIndex() == -1:
                preset.j_ssh_preset = ""
            else:
                preset.j_ssh_preset = self.ui.jobSshPresetComboBox.currentData()

        preset.j_execution_type = UiMultiJobDialog.REMOTE_LABEL
        if self.ui.jobSshPresetComboBox.currentText() == UiMultiJobDialog.SSH_LOCAL_EXEC:
            if self.ui.jobPbsPresetComboBox.currentText() == UiMultiJobDialog.PBS_OPTION_NONE:
                preset.j_execution_type = UiMultiJobDialog.EXEC_LABEL
            else:
                preset.j_execution_type = UiMultiJobDialog.PBS_LABEL
        elif self.ui.jobPbsPresetComboBox.currentText() == UiMultiJobDialog.PBS_OPTION_NONE:
            preset.j_remote_execution_type = UiMultiJobDialog.EXEC_LABEL
        else:
            preset.j_remote_execution_type = UiMultiJobDialog.PBS_LABEL

        if self.ui.jobPbsPresetComboBox.isEnabled() and \
                self.ui.jobPbsPresetComboBox.currentIndex() != 0:
            if self.ui.jobPbsPresetComboBox.currentIndex() == -1:
                preset.j_pbs_preset = ""
            else:
                preset.j_pbs_preset = self.ui.jobPbsPresetComboBox.currentData()

        preset.log_level = self.ui.logLevelComboBox.currentData()
        preset.analysis = self.ui.analysisComboBox.currentText()
        preset.from_mj = self._from_mj
        return {
            "key": key,
            "preset": preset
        }

    def set_data(self, data=None, is_edit=False):
        # reset validation colors
        self.ui.validator.reset_colorize()
        self.ui.nameLineEdit.setStyleSheet(
                "QLineEdit { background-color: #ffffff }")
        if data:
            key = data["key"]
            preset = data["preset"]
            self.preset = preset
            self._from_mj = preset.from_mj
            self.ui.idLineEdit.setText(key)
            self.ui.nameLineEdit.setText(preset.name)
            self.ui.multiJobSshPresetComboBox.setCurrentIndex(
                self.ui.multiJobSshPresetComboBox.findData(
                    'local' if preset.mj_ssh_preset is None else preset.mj_ssh_preset))
            self.ui.multiJobPbsPresetComboBox.setCurrentIndex(
                self.ui.multiJobPbsPresetComboBox.findData(
                    'no PBS' if preset.mj_pbs_preset is None else preset.mj_pbs_preset))

            self.ui.jobSshPresetComboBox.setCurrentIndex(
                self.ui.jobSshPresetComboBox.findData(
                    'local' if preset.j_ssh_preset is None else preset.j_ssh_preset))
            self.ui.jobPbsPresetComboBox.setCurrentIndex(
                self.ui.jobPbsPresetComboBox.findData(
                    'no PBS' if preset.j_pbs_preset is None else preset.j_pbs_preset))
            self.ui.logLevelComboBox.setCurrentIndex(
                self.ui.logLevelComboBox.findData(preset.log_level))
            self.ui.analysisComboBox.setCurrentIndex(
                self.ui.analysisComboBox.findData(preset.analysis))
            if self._from_mj is not None:
                self.ui.analysisComboBox.setDisabled(True)
            self._handle_mj_ssh_changed(0)
            self._handle_j_ssh_changed(0)
            self.valid()
        else:
            self.ui.analysisComboBox.setEnabled(True)
            self.ui.idLineEdit.clear()
            self.ui.nameLineEdit.clear()
            #self.ui.resourceComboBox.setCurrentIndex(0)
            self.ui.multiJobSshPresetComboBox.setCurrentIndex(0)
            self.ui.multiJobPbsPresetComboBox.setCurrentIndex(0)
            self.ui.jobPbsPresetComboBox.setCurrentIndex(0)
            self.ui.analysisComboBox.setCurrentIndex(0)
            self.ui.logLevelComboBox.setCurrentIndex(1)

            self.update_mj_name()


class UiMultiJobDialog(UiFormDialog):
    """
    UI extensions of form dialog.
    """
    EXECUTE_USING_LABEL = "Execute using:"
    EXECUTION_TYPE_LABEL = "Execution type:"
    SSH_PRESET_LABEL = "SSH host:"
    PBS_PRESET_LABEL = "PBS options:"
    JOB_ENV_LABEL = "Job environment:"

    EXEC_LABEL = "EXEC"
    DELEGATOR_LABEL = "DELEGATOR"
    REMOTE_LABEL = "REMOTE"
    PBS_LABEL = "PBS"
    SSH_LOCAL_EXEC = "local"
    PBS_OPTION_NONE = "no PBS"

    def setup_ui(self, dialog):
        super().setup_ui(dialog)

        # dialog properties
        dialog.resize(500, 440)

        # validators
        self.validator = PresetsValidationColorizer()

        # form layout
        # hidden row
        self.idLabel = QtWidgets.QLabel(self.mainVerticalLayoutWidget)
        self.idLabel.setObjectName("idLabel")
        self.idLabel.setText("Id:")
        self.idLabel.setVisible(False)
        # self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole,
        #                         self.idLabel)
        self.idLineEdit = QtWidgets.QLineEdit(self.mainVerticalLayoutWidget)
        self.idLineEdit.setObjectName("idLineEdit")
        self.idLineEdit.setPlaceholderText("This should be hidden")
        self.idLineEdit.setVisible(False)
        # self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole,
        #                          self.idLineEdit)

        # 1 row
        self.analysisLabel = QtWidgets.QLabel(self.mainVerticalLayoutWidget)
        self.analysisLabel.setObjectName("analysisLabel")
        self.analysisLabel.setText("Analysis:")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole,
                                  self.analysisLabel)
        self.analysisComboBox = QtWidgets.QComboBox(
            self.mainVerticalLayoutWidget)
        self.analysisComboBox.setObjectName("analysisComboBox")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole,
                                  self.analysisComboBox)

        # separator
        sep = QtWidgets.QLabel(self.mainVerticalLayoutWidget)
        sep.setText("")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, sep)

        # font
        labelFont = QtGui.QFont()
        labelFont.setPointSize(11)
        labelFont.setWeight(65)

        # multijob label
        self.multiJobLabel = QtWidgets.QLabel(self.mainVerticalLayoutWidget)
        self.multiJobLabel.setFont(labelFont)
        self.multiJobLabel.setText("MultiJob")
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.LabelRole,
                                  self.multiJobLabel)

        # 4 row
        self.multiJobSshPresetLabel = QtWidgets.QLabel(self.mainVerticalLayoutWidget)
        self.multiJobSshPresetLabel.setText(self.SSH_PRESET_LABEL)
        self.formLayout.setWidget(4, QtWidgets.QFormLayout.LabelRole,
                                  self.multiJobSshPresetLabel)
        self.multiJobSshPresetComboBox = QtWidgets.QComboBox(
            self.mainVerticalLayoutWidget)
        self.validator.add('mj_ssh_preset', self.multiJobSshPresetComboBox)
        self.formLayout.setWidget(4, QtWidgets.QFormLayout.FieldRole,
                                  self.multiJobSshPresetComboBox)

        # 5 row
        self.multiJobPbsPresetLabel = QtWidgets.QLabel(self.mainVerticalLayoutWidget)
        self.multiJobPbsPresetLabel.setText(self.PBS_PRESET_LABEL)
        self.formLayout.setWidget(5, QtWidgets.QFormLayout.LabelRole,
                                  self.multiJobPbsPresetLabel)
        self.multiJobPbsPresetComboBox = QtWidgets.QComboBox(
            self.mainVerticalLayoutWidget)
        self.validator.add('mj_pbs_preset', self.multiJobPbsPresetComboBox)
        self.formLayout.setWidget(5, QtWidgets.QFormLayout.FieldRole,
                                  self.multiJobPbsPresetComboBox)

        # separator
        sep = QtWidgets.QLabel(self.mainVerticalLayoutWidget)
        sep.setText("")
        self.formLayout.setWidget(6, QtWidgets.QFormLayout.LabelRole, sep)

        # job label
        self.jobLabel = QtWidgets.QLabel(self.mainVerticalLayoutWidget)
        self.jobLabel.setFont(labelFont)
        self.jobLabel.setText("Job")
        self.formLayout.setWidget(7, QtWidgets.QFormLayout.LabelRole,
                                  self.jobLabel)

        # 8 row
        self.jobSshPresetLabel = QtWidgets.QLabel(self.mainVerticalLayoutWidget)
        self.jobSshPresetLabel.setText(self.SSH_PRESET_LABEL)
        self.formLayout.setWidget(8, QtWidgets.QFormLayout.LabelRole,
                                  self.jobSshPresetLabel)
        self.jobSshPresetComboBox = QtWidgets.QComboBox(
            self.mainVerticalLayoutWidget)
        self.validator.add('j_ssh_preset', self.jobSshPresetComboBox)
        self.formLayout.setWidget(8, QtWidgets.QFormLayout.FieldRole,
                                  self.jobSshPresetComboBox)

        # 9 row
        self.jobPbsPresetLabel = QtWidgets.QLabel(self.mainVerticalLayoutWidget)
        self.jobPbsPresetLabel.setText(self.PBS_PRESET_LABEL)
        self.formLayout.setWidget(9, QtWidgets.QFormLayout.LabelRole,
                                  self.jobPbsPresetLabel)
        self.jobPbsPresetComboBox = QtWidgets.QComboBox(
            self.mainVerticalLayoutWidget)
        self.validator.add('j_pbs_preset', self.jobPbsPresetComboBox)
        self.formLayout.setWidget(9, QtWidgets.QFormLayout.FieldRole,
                                  self.jobPbsPresetComboBox)

        # separator
        sep = QtWidgets.QLabel(self.mainVerticalLayoutWidget)
        sep.setText("")
        self.formLayout.setWidget(10, QtWidgets.QFormLayout.LabelRole, sep)

        # 11 row
        self.nameLabel = QtWidgets.QLabel(self.mainVerticalLayoutWidget)
        self.nameLabel.setObjectName("nameLabel")
        self.nameLabel.setText("Name:")
        self.formLayout.setWidget(11, QtWidgets.QFormLayout.LabelRole,
                                  self.nameLabel)
        self.nameLineEdit = QtWidgets.QLineEdit(self.mainVerticalLayoutWidget)
        self.nameLineEdit.setObjectName("nameLineEdit")
        self.nameLineEdit.setPlaceholderText("Only alphanumeric characters "
                                             "and - or _")
        self.nameLineEdit.setProperty("clearButtonEnabled", True)
        self.validator.add('name',self.nameLineEdit)
        self.formLayout.setWidget(11, QtWidgets.QFormLayout.FieldRole,
                                  self.nameLineEdit)

        # 12 row
        self.logLevelLabel = QtWidgets.QLabel(self.mainVerticalLayoutWidget)
        self.logLevelLabel.setObjectName("logLevelLabel")
        self.logLevelLabel.setText("Log Level:")
        self.formLayout.setWidget(12, QtWidgets.QFormLayout.LabelRole,
                                  self.logLevelLabel)
        self.logLevelComboBox = QtWidgets.QComboBox(
            self.mainVerticalLayoutWidget)
        self.logLevelComboBox.setObjectName("logLevelComboBox")
        self.logLevelComboBox.addItem(logging.getLevelName(logging.INFO),
                                      logging.INFO)
        self.logLevelComboBox.addItem(logging.getLevelName(logging.WARNING),
                                      logging.WARNING)
        self.logLevelComboBox.setCurrentIndex(0)
        self.formLayout.setWidget(12, QtWidgets.QFormLayout.FieldRole,
                                  self.logLevelComboBox)

        return dialog
