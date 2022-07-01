# -*- coding: utf-8 -*-
"""

"""

__all__ = ['LocalModuleConfigurationWidget']

import os
from PySide2 import QtCore, QtGui, QtWidgets
from typing import Optional, Iterable, Mapping, Dict, Sequence, Union, Any
from qudi.core import Connector, ConfigOption
from qudi.util.paths import get_artwork_dir
from qudi.util.widgets.lines import HorizontalLine
from qudi.tools.config_editor.module_finder import QudiModules
from qudi.tools.config_editor.custom_option_editor import CustomOptionConfigurationWidget


class CustomConnectorConfigurationWidget(QtWidgets.QWidget):
    """
    """
    def __init__(self,
                 forbidden_names: Optional[Iterable[str]] = None,
                 custom_connectors: Optional[Mapping[str, Union[None, str]]] = None,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)

        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setColumnStretch(2, 1)
        self.setLayout(layout)

        icons_dir = os.path.join(get_artwork_dir(), 'icons')
        self.add_connector_button = QtWidgets.QToolButton()
        self.add_connector_button.setIcon(QtGui.QIcon(os.path.join(icons_dir, 'list-add')))
        self.add_connector_button.setToolTip('Add a custom connector with given name.')
        self.add_connector_button.clicked.connect(self.add_connector)
        self.connector_name_lineedit = QtWidgets.QLineEdit()
        self.connector_name_lineedit.setPlaceholderText('Enter custom connector name')
        layout.addWidget(self.add_connector_button, 0, 0, 1, 1)
        layout.addWidget(self.connector_name_lineedit, 0, 1, 1, 2)

        # Remove icons reused for each custom connector
        self._remove_icon = QtGui.QIcon(os.path.join(icons_dir, 'list-remove'))
        # Keep track of custom connector editor widgets
        self._connector_widgets = dict()
        # forbidden connector names
        self._forbidden_names = frozenset() if forbidden_names is None else frozenset(
            forbidden_names)

        self.set_connectors(custom_connectors)

    @property
    def connectors(self) -> Dict[str, Union[None, str]]:
        conn = {
            name: widgets[2].text().strip() for name, widgets in self._connector_widgets.items()
        }
        return {name: target if target else None for name, target in conn.items()}

    def set_connectors(self, connections: Union[None, Mapping[str, Union[None, str]]]) -> None:
        self.clear_connectors()
        if connections:
            for name, target in connections.items():
                self.add_connector(name)
                self._connector_widgets[name][2].setText('' if target is None else str(target))

    @QtCore.Slot()
    def add_connector(self, name: Optional[str] = None) -> None:
        name = name if isinstance(name, str) else self.connector_name_lineedit.text().strip()
        if name and (name not in self._forbidden_names) and (name not in self._connector_widgets):
            self.connector_name_lineedit.clear()
            label = QtWidgets.QLabel(f'{name}:')
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            editor = QtWidgets.QLineEdit()
            remove_button = QtWidgets.QToolButton()
            remove_button.setIcon(self._remove_icon)
            remove_button.clicked.connect(lambda: self.remove_connector(name))
            row = len(self._connector_widgets) + 1
            layout = self.layout()
            layout.addWidget(remove_button, row, 0)
            layout.addWidget(label, row, 1)
            layout.addWidget(editor, row, 2)
            self._connector_widgets[name] = (remove_button, label, editor)

    def remove_connector(self, name: Optional[str] = None) -> None:
        if name not in self._connector_widgets:
            return

        layout = self.layout()

        # Remove all widgets from layout
        for button, label, editor in reversed(list(self._connector_widgets.values())):
            layout.removeWidget(button)
            layout.removeWidget(label)
            layout.removeWidget(editor)

        # Delete widgets for row to remove
        button, label, editor = self._connector_widgets.pop(name)
        button.clicked.disconnect()
        button.setParent(None)
        label.setParent(None)
        editor.setParent(None)
        button.deleteLater()
        label.deleteLater()
        editor.deleteLater()

        # Add all remaining widgets to layout again
        for row, (button, label, editor) in enumerate(self._connector_widgets.values(), 1):
            layout.addWidget(button, row, 0)
            layout.addWidget(label, row, 1)
            layout.addWidget(editor, row, 2)

    def clear_connectors(self) -> None:
        layout = self.layout()
        widgets = list(self._connector_widgets.values())
        self._connector_widgets.clear()
        for button, label, editor in reversed(widgets):
            layout.removeWidget(button)
            layout.removeWidget(label)
            layout.removeWidget(editor)
            button.setParent(None)
            label.setParent(None)
            editor.setParent(None)
            button.deleteLater()
            label.deleteLater()
            editor.deleteLater()


class ConnectorConfigurationWidget(QtWidgets.QWidget):
    """
    """
    def __init__(self,
                 connectors: Mapping[str, bool],
                 valid_targets: Mapping[str, Sequence[str]],
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)

        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setColumnStretch(1, 1)
        self.setLayout(layout)

        # Keep track of connector editor widgets
        self._connector_editors = dict()
        for row, (name, optional) in enumerate(connectors.items()):
            if optional:
                label = QtWidgets.QLabel(f'{name}:')
            else:
                label = QtWidgets.QLabel(f'* {name}:')
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            editor = QtWidgets.QComboBox()
            editor.addItem('')
            editor.addItems(valid_targets[name])
            editor.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
            layout.addWidget(label, row, 0)
            layout.addWidget(editor, row, 1)
            self._connector_editors[name] = editor

    @property
    def connectors(self) -> Dict[str, Union[None, str]]:
        conn = {name: editor.currentText() for name, editor in self._connector_editors.items()}
        return {name: target if target else None for name, target in conn.items()}

    def set_connectors(self, conn: Union[None, Mapping[str, Union[None, str]]]) -> None:
        if conn is None:
            for editor in self._connector_editors.values():
                editor.setCurrentIndex(0)
        else:
            for name, target in conn.items():
                editor = self._connector_editors[name]
                index = max(0, editor.findText(target)) if target else 0
                editor.setCurrentIndex(index)


class OptionConfigurationWidget(QtWidgets.QWidget):
    """
    """
    def __init__(self,
                 options: Mapping[str, bool],
                 default_values: Optional[Mapping[str, Any]] = None,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)

        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setColumnStretch(1, 1)
        self.setLayout(layout)

        self._default_values = dict() if default_values is None else default_values.copy()

        # Keep track of option editor widgets
        self._option_editors = dict()
        for row, (name, optional) in enumerate(options.items()):
            if optional:
                label = QtWidgets.QLabel(f'{name}:')
            else:
                label = QtWidgets.QLabel(f'* {name}:')
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            editor = QtWidgets.QLineEdit(str(self._default_values.get(name, '')))
            editor.setPlaceholderText('text parsed by eval()')
            layout.addWidget(label, row, 0)
            layout.addWidget(editor, row, 1)
            self._option_editors[name] = editor

    @property
    def options(self) -> Dict[str, Any]:
        opt = dict()
        for name, editor in self._option_editors.items():
            text = editor.text().strip()
            try:
                opt[name] = eval(text)
            except (NameError, SyntaxError, ValueError):
                opt[name] = None
        return opt

    def set_options(self, options: Union[None, Mapping[str, Any]]) -> None:
        if options is None:
            for editor in self._option_editors.values():
                editor.setText('')
        else:
            for name, value in options.items():
                self._option_editors[name].setText(repr(value))


class LocalModuleConfigurationWidget(QtWidgets.QWidget):
    """
    """
    sigModuleNameChanged = QtCore.Signal(str)

    def __init__(self,
                 module: str,
                 qudi_modules: QudiModules,
                 named_modules: Optional[Mapping[str, str]] = None,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)

        self._qudi_modules = qudi_modules
        self._named_modules = dict() if named_modules is None else named_modules
        self._module = module
        # self._base = module.split('.', 1)[0]

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Module name editor
        self.module_name_lineedit = QtWidgets.QLineEdit('' if name is None else name)
        self.module_name_lineedit.setPlaceholderText('* enter unique name')
        self.module_name_lineedit.setAlignment(QtCore.Qt.AlignCenter)
        self.module_name_lineedit.textChanged.connect(self.sigModuleNameChanged)
        font = self.module_name_lineedit.font()
        font.setPointSize(16)
        font.setBold(True)
        self.module_name_lineedit.setFont(font)
        layout.addWidget(self.module_name_lineedit)

        # module import path
        label = QtWidgets.QLabel(module)
        label.setAlignment(QtCore.Qt.AlignCenter)
        font.setPointSize(12)
        label.setFont(font)
        layout.addWidget(label)

        layout.addStretch(1)

        # allow_remote flag editor
        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.setStretch(1, 1)
        label = QtWidgets.QLabel('Allow remote connection:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.allow_remote_checkbox = QtWidgets.QCheckBox()
        sub_layout.addWidget(label)
        sub_layout.addWidget(self.allow_remote_checkbox)
        layout.addLayout(sub_layout)

        # Add separator
        layout.addWidget(HorizontalLine())

        # ConfigOption editors
        config_options = qudi_modules.module_config_options(module)
        self.options_editor = OptionConfigurationWidget(
            options={opt.name: opt.optional for opt in config_options},
            default_values={opt.name: opt.default for opt in config_options}
        )
        layout.addWidget(self.options_editor)

        self.custom_options_editor = CustomOptionConfigurationWidget(
            forbidden_names=[opt.name for opt in config_options]
        )
        layout.addWidget(self.custom_options_editor)

        # Add separator
        layout.addWidget(HorizontalLine())

        # Connector editors
        connectors = qudi_modules.module_connectors(module)
        connector_targets = {name: [n for n, mod in named_modules.items() if mod in valid_mod] for
                             name, valid_mod in
                             qudi_modules.module_connector_targets(module).items()}
        self.connectors_editor = ConnectorConfigurationWidget(
            connectors={conn.name: conn.optional for conn in connectors},
            valid_targets=connector_targets
        )
        layout.addWidget(self.connectors_editor)

        self.custom_connectors_editor = CustomConnectorConfigurationWidget(
            forbidden_names=[conn.name for conn in connectors]
        )
        layout.addWidget(self.custom_connectors_editor)

        # Add stretch to bottom
        layout.addStretch(1)

        # Renmember known Connectors and ConfigOptions
        self._default_options = {opt.name: opt.default for opt in config_options}
        self._connector_names = frozenset(conn.name for conn in connectors)

    @property
    def name(self) -> str:
        return self.module_name_lineedit.text()

    @property
    def config(self) -> Dict[str, Dict[str, Union[str, bool, Dict[str, str], Dict[str, Any]]]]:
        options = self.options_editor.options
        options.update(self.custom_options_editor.options)
        connections = self.connectors_editor.connectors
        connections.update(self.custom_connectors_editor.connectors)
        configuration = {'module.Class': self._module,
                         'allow_remote': self.allow_remote_checkbox.isChecked(),
                         'options'     : options,
                         'connect'     : connections}
        return {self.name: configuration}

    def set_config(self,
                   cfg: Union[None, Dict[str, Dict[str, Union[str, bool, Dict[str, str], Dict[str, Any]]]]]
                   ) -> None:
        if cfg:
            name = list(cfg)[0]
            configuration = cfg[name]
            config_opts = configuration.get('options', dict())
            config_conn = configuration.get('connect', dict())
            options = {name: config_opts.get(name, default) for name, default in
                       self._default_options.items()}
            custom_options = {name: val for name, val in config_opts.items() if name not in options}
            conn = {name: config_conn.get(name, None) for name in self._connector_names}
            custom_conn = {name: val for name, val in config_conn.items() if name not in conn}
            allow_remote = configuration.get('allow_remote', False)
        else:
            options = custom_options = conn = custom_conn = None
            allow_remote = False
        self.allow_remote_checkbox.setChecked(allow_remote)
        self.options_editor.set_options(options)
        self.custom_options_editor.set_options(custom_options)
        self.connectors_editor.set_connectors(conn)
        self.custom_connectors_editor.set_connectors(custom_conn)


class ModuleEditorWidget(QtWidgets.QWidget):
    """
    """
    sigModuleConfigFinished = QtCore.Signal(str, dict, dict, dict)

    _add_icon_path = os.path.join(get_artwork_dir(), 'icons', 'list-add')
    _remove_icon_path = os.path.join(get_artwork_dir(), 'icons', 'list-remove')

    def __init__(self, qudi_modules: QudiModules, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)
        self.setLayout(layout)

        self.placeholder_label = QtWidgets.QLabel(
            'Please select a module to configure from the module tree.'
        )
        font = self.placeholder_label.font()
        font.setBold(True)
        font.setPointSize(10)
        self.placeholder_label.setFont(font)
        self.placeholder_label.setAlignment(QtCore.Qt.AlignCenter)
        self.placeholder_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                             QtWidgets.QSizePolicy.Expanding)
        layout.addWidget(self.placeholder_label)

        self._qudi_modules = qudi_modules
        self._current_editor = None

    def open_module_editor(self,
                           module: str,
                           config: Optional[Dict[str, Dict[str, Union[str, bool, Dict[str, str], Dict[str, Any]]]]] = None,
                           named_modules: Optional[Mapping[str, str]] = None
                           ) -> None:
        if self._current_editor is not None:
            self.close_module_editor()

        editor = LocalModuleConfigurationWidget(module=module,
                                                qudi_modules=self._qudi_modules,
                                                named_modules=named_modules)
        editor.set_config(config)
        layout = self.layout()
        self.placeholder_label.hide()
        layout.addWidget(editor)
        self._current_editor = editor

    def close_module_editor(self):
        if self._current_editor is None:
            return
        layout = self.layout()
        layout.removeWidget(self._current_editor)
        self.placeholder_label.show()
        self._current_editor.setParent(None)
        self._current_editor.deleteLater()
        self._current_editor = None
