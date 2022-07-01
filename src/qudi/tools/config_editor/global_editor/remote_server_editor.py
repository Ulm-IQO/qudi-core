# -*- coding: utf-8 -*-

"""
QWidget serving as editor for remote modules server configuration.

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

__all__ = ['RemoteServerConfigurationWidget']

from PySide2 import QtCore, QtWidgets
from typing import Optional, Mapping, Union, Dict

from qudi.util.widgets.path_line_edit import PathLineEdit as _PathLineEdit


class RemoteServerConfigurationWidget(QtWidgets.QWidget):
    """ Remote modules server configuration editor widget.
    """
    def __init__(self,
                 server_config: Optional[Mapping[str, Union[int, str]]] = None,
                 **kwargs
                 ) -> None:
        super().__init__(**kwargs)

        # Create main layout
        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setColumnStretch(1, 1)
        self.setLayout(layout)

        # Create editors
        self._editor_widgets = list()

        label = QtWidgets.QLabel('Remote modules server:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.enable_checkbox = QtWidgets.QCheckBox()
        self.enable_checkbox.setChecked(True)
        self.enable_checkbox.setToolTip(
            'Whether qudi should start a remote modules server at all.\nYou will not be able to '
            'communicate with remote qudi instances if this is disabled.'
        )
        layout.addWidget(label, 0, 0)
        layout.addWidget(self.enable_checkbox, 0, 1)

        label = QtWidgets.QLabel('Host address:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.host_lineedit = QtWidgets.QLineEdit('localhost')
        self.host_lineedit.setToolTip(
            'The host address to share qudi modules with other qudi instances'
        )
        layout.addWidget(label, 1, 0)
        layout.addWidget(self.host_lineedit, 1, 1)
        self._editor_widgets.append((label, self.host_lineedit))

        label = QtWidgets.QLabel('Port:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.port_spinbox = QtWidgets.QSpinBox()
        self.port_spinbox.setToolTip('Port number for the remote modules server to bind to')
        self.port_spinbox.setRange(0, 65535)
        self.port_spinbox.setValue(12345)
        layout.addWidget(label, 2, 0)
        layout.addWidget(self.port_spinbox, 2, 1)
        self._editor_widgets.append((label, self.port_spinbox))

        label = QtWidgets.QLabel('Certificate file:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.certfile_lineedit = _PathLineEdit(dialog_caption='Select SSL Certificate File',
                                               follow_symlinks=True)
        self.certfile_lineedit.setPlaceholderText('No certificate')
        self.certfile_lineedit.setToolTip('SSL certificate file path for the remote module server')
        layout.addWidget(label, 3, 0)
        layout.addWidget(self.certfile_lineedit, 3, 1)
        self._editor_widgets.append((label, self.certfile_lineedit))

        label = QtWidgets.QLabel('Key file:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.keyfile_lineedit = _PathLineEdit(dialog_caption='Select SSL Key File',
                                              follow_symlinks=True)
        self.keyfile_lineedit.setPlaceholderText('No key')
        self.keyfile_lineedit.setToolTip('SSL key file path for the remote module server')
        layout.addWidget(label, 4, 0)
        layout.addWidget(self.keyfile_lineedit, 4, 1)
        self._editor_widgets.append((label, self.keyfile_lineedit))

        self.enable_checkbox.toggled.connect(self._toggle_editors)
        self.set_config(server_config)

    @property
    def config(self) -> Union[None, Dict[str, Union[None, int, str]]]:
        if self.enable_checkbox.isChecked():
            try:
                certfile = self.certfile_lineedit.paths[0]
            except IndexError:
                certfile = None
            try:
                keyfile = self.keyfile_lineedit.paths[0]
            except IndexError:
                keyfile = None
            host = self.host_lineedit.text().strip()
            return {'address' : host if host else None,
                    'port'    : self.port_spinbox.value(),
                    'certfile': certfile,
                    'keyfile' : keyfile}
        return None

    def set_config(self, config: Union[None, Mapping[str, Union[None, int, str]]]) -> None:
        if config:
            self.host_lineedit.setText(config.get('address', 'localhost'))
            self.port_lineedit.setValue(config.get('port', 12345))
            self.certfile_lineedit.setText(config.get('certfile', ''))
            self.keyfile_lineedit.setText(config.get('keyfile', ''))
            self.enable_checkbox.setChecked(True)
        else:
            self.enable_checkbox.setChecked(False)

    @QtCore.Slot(bool)
    def _toggle_editors(self, enabled: bool) -> None:
        for label, editor in self._editor_widgets:
            editor.setVisible(enabled)
            label.setVisible(enabled)


