# -*- coding: utf-8 -*-

"""
Configuration editor App for creation and editing of qudi configuration files.

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

__all__ = ('main', 'ConfigurationEditorMainWindow', 'ConfigurationEditor')

import os
import sys
from typing import Optional, Mapping, Dict, Any
from PySide2 import QtCore, QtGui, QtWidgets
from qudi.util.paths import get_main_dir, get_default_config_dir, get_artwork_dir
from qudi.core.config import Configuration

from qudi.tools.config_editor.module_selector import ModuleSelector
from qudi.tools.config_editor.module_editor import ModuleEditorWidget
from qudi.tools.config_editor.global_editor import GlobalEditorWidget
from qudi.tools.config_editor.tree_widgets import ConfigModulesTreeWidget
from qudi.tools.config_editor.module_finder import QudiModules

try:
    import matplotlib
    matplotlib.use('agg')
except ImportError:
    pass

# Enable the High DPI scaling support of Qt5
os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'

if sys.platform == 'win32':
    # Set QT_LOGGING_RULES environment variable to suppress qt.svg related warnings that otherwise
    # spam the log due to some known Qt5 bugs, e.g. https://bugreports.qt.io/browse/QTBUG-52079
    os.environ['QT_LOGGING_RULES'] = 'qt.svg.warning=false'
else:
    # The following will prevent Qt to spam the logs on X11 systems with enough messages
    # to significantly slow the program down. Most of those warnings should have been
    # notice level or lower. This is a known problem since Qt does not fully comply to X11.
    os.environ['QT_LOGGING_RULES'] = '*.debug=false;*.info=false;*.notice=false;*.warning=false'


class ConfigurationEditor(QtWidgets.QMainWindow):
    """
    """
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.setWindowTitle('Qudi Config Editor')
        screen_size = QtWidgets.QApplication.instance().primaryScreen().availableSize()
        self.resize((screen_size.width() * 3) // 4, (screen_size.height() * 3) // 4)

        self.qudi_environment = QudiModules()

        self.module_tree_widget = ConfigModulesTreeWidget()
        self.module_tree_widget.itemChanged.connect(self._module_renamed_by_tree)
        self.module_tree_widget.itemSelectionChanged.connect(self._module_selection_changed)

        self.module_config_editor = ModuleEditorWidget(qudi_modules=self.qudi_environment)
        self.module_config_editor.sigModuleRenamed.connect(self._module_renamed_by_editor)

        self.global_config_editor = GlobalEditorWidget()

        label = QtWidgets.QLabel('Included Modules')
        label.setAlignment(QtCore.Qt.AlignCenter)
        font = label.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 4)
        label.setFont(font)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.module_tree_widget)
        layout.addWidget(self.global_config_editor)
        layout.setStretch(1, 1)
        left_widget = QtWidgets.QWidget()
        left_widget.setLayout(layout)

        label = QtWidgets.QLabel('Module Configuration')
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setFont(font)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.module_config_editor)
        label = QtWidgets.QLabel('Mandatory fields/options/connectors are marked with *')
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label)
        layout.setStretch(1, 1)
        right_widget = QtWidgets.QWidget()
        right_widget.setLayout(layout)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        self.setCentralWidget(splitter)

        # Main window actions
        icon_dir = os.path.join(get_main_dir(), 'artwork', 'icons')
        quit_icon = QtGui.QIcon(os.path.join(icon_dir, 'application-exit'))
        self.quit_action = QtWidgets.QAction(quit_icon, 'Quit')
        self.quit_action.setShortcut(QtGui.QKeySequence('Ctrl+Q'))
        load_icon = QtGui.QIcon(os.path.join(icon_dir, 'document-open'))
        self.load_action = QtWidgets.QAction(load_icon, 'Load')
        self.load_action.setShortcut(QtGui.QKeySequence('Ctrl+L'))
        self.load_action.setToolTip('Load a qudi configuration to edit from file.')
        save_icon = QtGui.QIcon(os.path.join(icon_dir, 'document-save'))
        self.save_action = QtWidgets.QAction(save_icon, 'Save')
        self.save_action.setShortcut(QtGui.QKeySequence('Ctrl+S'))
        self.save_action.setToolTip('Save the current qudi configuration to file.')
        self.save_as_action = QtWidgets.QAction('Save as ...')
        new_icon = QtGui.QIcon(os.path.join(icon_dir, 'document-new'))
        self.new_action = QtWidgets.QAction(new_icon, 'New')
        self.new_action.setShortcut(QtGui.QKeySequence('Ctrl+N'))
        self.new_action.setToolTip('Create a new qudi configuration from scratch.')
        select_icon = QtGui.QIcon(os.path.join(icon_dir, 'configure'))
        self.select_modules_action = QtWidgets.QAction(select_icon, 'Select Modules')
        self.select_modules_action.setShortcut(QtGui.QKeySequence('Ctrl+M'))
        self.select_modules_action.setToolTip(
            'Open an editor to select the modules to include in config.'
        )
        # Connect actions
        self.quit_action.triggered.connect(self.close)
        self.new_action.triggered.connect(self.new_config)
        self.load_action.triggered.connect(self.prompt_load_config)
        self.save_action.triggered.connect(self.save_config)
        self.save_as_action.triggered.connect(self.prompt_save_config)
        self.select_modules_action.triggered.connect(self.select_modules)

        # Create menu bar
        menu_bar = QtWidgets.QMenuBar()
        file_menu = QtWidgets.QMenu('File')
        menu_bar.addMenu(file_menu)
        file_menu.addAction(self.new_action)
        file_menu.addSeparator()
        file_menu.addAction(self.load_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)
        file_menu = QtWidgets.QMenu('Edit')
        menu_bar.addMenu(file_menu)
        file_menu.addAction(self.select_modules_action)
        self.setMenuBar(menu_bar)

        # Create toolbar
        toolbar = QtWidgets.QToolBar()
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        toolbar.addAction(self.new_action)
        toolbar.addAction(self.load_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.select_modules_action)
        toolbar.setFloatable(False)
        self.addToolBar(toolbar)

        # Process variables
        self._editor_item = None
        self._config_map = dict()
        self._current_file_path = None

    @QtCore.Slot()
    def _module_selection_changed(self):
        selected_items = self.module_tree_widget.selectedItems()
        if not selected_items:
            self.module_config_editor.close_editor()
            self._editor_item = None
            return

        item = selected_items[0]
        if item is not self._editor_item:
            base = item.parent().text(0).lower()
            module = f'{base}.{item.text(2)}'
            name = item.text(1)

            # Get current module config dict
            config = self._config_map.get(base, dict()).get(name, None)

            # Sort out available connectors and targets as well as module config options
            if module == '<REMOTE MODULE>':
                self.module_config_editor.open_remote_module(name, config=config)
            else:
                self.module_config_editor.open_local_module(
                    module_class=module,
                    named_modules=self.module_tree_widget.modules[0],
                    name=name,
                    config=config
                )
            self._editor_item = item

    @QtCore.Slot()
    def select_modules(self):
        self.module_config_editor.close_editor()
        available = self.qudi_environment.available_modules
        named_selected, unnamed_selected = self.module_tree_widget.modules
        selector_dialog = ModuleSelector(available_modules=available,
                                         named_modules=named_selected,
                                         unnamed_modules=unnamed_selected)
        if selector_dialog.exec_():
            # Recycle old module names if identical modules are selected but not named
            new_named_selected, new_unnamed_selected = selector_dialog.selected_modules
            recycled_named_selected = {
                name: mod for name, mod in named_selected.items() if
                (name not in new_named_selected) and (mod in new_unnamed_selected)
            }
            new_named_selected.update(recycled_named_selected)
            for mod in recycled_named_selected.values():
                new_unnamed_selected.remove(mod)
            # Set modules in main window
            self.module_tree_widget.set_modules(named_modules=new_named_selected,
                                                unnamed_modules=new_unnamed_selected)

    def new_config(self):
        self._current_file_path = None
        self._config_map = dict()
        self.module_config_editor.close_editor()
        self.module_tree_widget.set_modules(dict())
        self.global_config_editor.open_editor(None)
        self.select_modules()

    def prompt_load_config(self):
        file_path = QtWidgets.QFileDialog.getOpenFileName(
            self,
            'Qudi Config Editor: Load Configuration...',
            get_default_config_dir(),
            'Config files (*.cfg)')[0]
        if file_path:
            self.module_config_editor.close_editor()
            config = Configuration()
            config.load(file_path, set_default=False)
            self._config_map = config.config_map
            self._current_file_path = file_path
            modules = self._get_modules_from_config(self._config_map)
            global_cfg = self._config_map.get('global', dict())
            self.module_tree_widget.set_modules(named_modules=modules)
            self.global_config_editor.open_editor(global_cfg)

    def prompt_save_config(self):
        file_path = QtWidgets.QFileDialog.getSaveFileName(
            self,
            'Qudi Config Editor: Save Configuration...',
            get_default_config_dir() if self._current_file_path is None else os.path.dirname(
                self._current_file_path),
            'Config files (*.cfg)')[0]
        if file_path:
            config = Configuration(config=self._config_map)
            config.dump(file_path)
            self._current_file_path = file_path

    def prompt_overwrite(self, file_path):
        answer = QtWidgets.QMessageBox.question(
            self,
            'Qudi Config Editor: Overwrite?',
            f'Do you really want to overwrite existing Qudi configuration at\n"{file_path}"?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No)
        return answer == QtWidgets.QMessageBox.Yes

    def save_config(self):
        if self._current_file_path is None:
            self.prompt_save_config()
        elif os.path.exists(self._current_file_path):
            if self.prompt_overwrite(self._current_file_path):
                config = Configuration(config=self._config_map)
                config.dump(self._current_file_path)
            else:
                self.prompt_save_config()
        else:
            config = Configuration(config=self._config_map)
            config.dump(self._current_file_path)

    def prompt_close(self):
        answer = QtWidgets.QMessageBox.question(
            self,
            'Qudi Config Editor: Quit?',
            'Do you really want to quit the Qudi configuration editor?\nAll unsaved work will be '
            'lost.',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        return answer == QtWidgets.QMessageBox.Yes

    def closeEvent(self, event):
        if self.prompt_close():
            event.accept()
        else:
            event.ignore()

    @staticmethod
    def _get_modules_from_config(config: Mapping[str, Any]) -> Dict[str, str]:
        modules = {name: 'gui.' + cfg.get('module.Class', '<REMOTE MODULE>') for name, cfg in
                   config.get('gui', dict()).items()}
        modules.update({name: 'logic.' + cfg.get('module.Class', '<REMOTE MODULE>') for name, cfg in
                        config.get('logic', dict()).items()})
        modules.update(
            {name: 'hardware.' + cfg.get('module.Class', '<REMOTE MODULE>') for name, cfg in
             config.get('hardware', dict()).items()}
        )
        return modules

    @QtCore.Slot(QtWidgets.QTreeWidgetItem, int)
    def _module_renamed_by_tree(self, item, column):
        if column != 1 or item is None or item.parent() is None:
            return

        name = item.text(1)
        if item is self._editor_item:
            self.module_config_editor.set_module_name(name)

    @QtCore.Slot(str)
    def _module_renamed_by_editor(self, name: str) -> None:
        self.module_tree_widget.blockSignals(True)
        try:
            self._editor_item.setText(1, name)
        except AttributeError:
            pass
        finally:
            self.module_tree_widget.blockSignals(False)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == QtCore.Qt.Key_Escape:
            self.module_tree_widget.clearSelection()
            event.accept()
        else:
            super().keyPressEvent(event)


class ConfigurationEditorApp(QtWidgets.QApplication):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        app_icon = QtGui.QIcon(os.path.join(get_artwork_dir(), 'logo', 'logo-qudi.svg'))
        self.setWindowIcon(app_icon)


def main():
    app = ConfigurationEditorApp(sys.argv)
    # init editor QMainWindow and show
    editor = ConfigurationEditor()
    editor.show()
    # Start event loop
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
