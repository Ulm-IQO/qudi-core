# -*- coding: utf-8 -*-
"""
This file contains a settings dialog for the qudi main GUI.

Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-core/>

This file is part of qudi.

Qudi is free software: you can redistribute it and/or modify it under the terms of
the GNU Lesser General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with qudi.
If not, see <https://www.gnu.org/licenses/>.
"""

from PySide2 import QtCore, QtWidgets
from qudi.util.widgets.scientific_spinbox import ScienSpinBox


class SettingsDialog(QtWidgets.QDialog):
    """
    Custom QDialog widget for configuration of the qudi main GUI
    """
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.setWindowTitle('Qudi: Main GUI settings')

        # Create main layout
        # Add widgets to layout and set as main layout
        layout = QtWidgets.QGridLayout()
        layout.setRowStretch(1, 1)
        self.setLayout(layout)

        # Create widgets and add them to the layout
        self.font_size_spinbox = QtWidgets.QSpinBox()
        self.font_size_spinbox.setObjectName('fontSizeSpinBox')
        self.font_size_spinbox.setMinimum(5)
        self.font_size_spinbox.setValue(10)
        label = QtWidgets.QLabel('Console font size:')
        label.setObjectName('fontSizeLabel')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 0, 0)
        layout.addWidget(self.font_size_spinbox, 0, 1)

        self.show_error_popups_checkbox = QtWidgets.QCheckBox()
        self.show_error_popups_checkbox.setObjectName('showErrorPopupsCheckbox')
        self.show_error_popups_checkbox.setChecked(True)
        label = QtWidgets.QLabel('Show error popups:')
        label.setObjectName('showErrorPopupsLabel')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 1, 0)
        layout.addWidget(self.show_error_popups_checkbox, 1, 1)

        label = QtWidgets.QLabel("Automatic StatusVar saving")
        label.setObjectName("autoStatusVarSavingLabel")
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.checkbox_automatic_status_variable_dumping = QtWidgets.QCheckBox()
        self.checkbox_automatic_status_variable_dumping.setChecked(False)
        self.checkbox_automatic_status_variable_dumping.setToolTip(
            "Activate / Deactivate automatic dumping of status variables"
        )
        layout.addWidget(label, 2, 0)
        layout.addWidget(self.checkbox_automatic_status_variable_dumping, 2, 1)

        label = QtWidgets.QLabel("Automatic StatusVar saving interval")
        label.setObjectName("autoStatusVarSavingIntervalLabel")
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.dump_status_variables_interval_spinbox = ScienSpinBox()
        self.dump_status_variables_interval_spinbox.setToolTip(
            "Time interval for automatic dumping of status variables"
        )
        self.dump_status_variables_interval_spinbox.setSuffix("min")
        self.dump_status_variables_interval_spinbox.setMinimum(1)
        self.dump_status_variables_interval_spinbox.setMaximum(1440)
        self.dump_status_variables_interval_spinbox.setMinimumSize(QtCore.QSize(80, 0))
        self.dump_status_variables_interval_spinbox.setValue(1)
        layout.addWidget(label, 3, 0)
        layout.addWidget(self.dump_status_variables_interval_spinbox, 3, 1)

        buttonbox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok
                                               | QtWidgets.QDialogButtonBox.Cancel
                                               | QtWidgets.QDialogButtonBox.Apply)
        buttonbox.setOrientation(QtCore.Qt.Horizontal)
        layout.addWidget(buttonbox, 4, 0, 1, 2)

        # Add internal signals
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        buttonbox.button(buttonbox.Apply).clicked.connect(self.accepted)
