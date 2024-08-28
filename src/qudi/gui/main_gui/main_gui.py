# -*- coding: utf-8 -*-
""" This module contains the

Copyright (c) 2021-2024, the qudi developers. See the AUTHORS.md file at the top-level directory of
this distribution and on <https://github.com/Ulm-IQO/qudi-core/>

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

import os
import sys
import logging
import subprocess
import jupyter_client.kernelspec
from PySide2 import QtCore, QtWidgets
from qtconsole.manager import QtKernelManager
from typing import Optional
try:
    from git import Repo, InvalidGitRepositoryError
except ImportError:
    Repo = None
    InvalidGitRepositoryError = RuntimeError

from qudi.core.statusvariable import StatusVar
from qudi.core.threadmanager import ThreadManager
from qudi.util.paths import get_main_dir, get_default_config_dir
from qudi.gui.main_gui.errordialog import ErrorDialog
from qudi.gui.main_gui.mainwindow import QudiMainWindow
from qudi.core.module import GuiBase
from qudi.core.logger import get_signal_handler
from qudi.core.config import Configuration
from qudi.core.application import Qudi


class QudiMainGui(GuiBase):
    """ This class provides a GUI to the qudi main application object """
    _console_font_size = StatusVar(name='console_font_size', default=10)
    _show_error_popups = StatusVar(name='show_error_popups', default=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_dialog = None
        self.mw = None
        self._has_console = False  # Flag indicating if an IPython console is available
        self._qudi_main = Qudi.instance()

    def on_activate(self) -> None:
        """ Activation method called on change to active state.
        This method creates the Manager main window.
        """
        # Create main window and restore position
        self.mw = QudiMainWindow(module_manager=self._qudi_main.module_manager,
                                 debug_mode=self._qudi_main.debug_mode)
        self._restore_window_geometry(self.mw)
        # Create error dialog for error message popups
        self.error_dialog = ErrorDialog()
        self.error_dialog.set_enabled(self._show_error_popups)

        # Get qudi version number and configure statusbar and "about qudi" dialog
        version = self.get_qudi_version()
        if isinstance(version, str):
            self.mw.about_qudi_dialog.version_label.setText('version {0}'.format(version))
            self.mw.version_label.setText(
                '<a style=\"color: cyan;\"> version {0} </a>  configured from {1}'
                ''.format(version, self._configuration.file_path))
        else:
            self.mw.about_qudi_dialog.version_label.setText(
                '<a href=\"https://github.com/Ulm-IQO/qudi/commit/{0}\" style=\"color: cyan;\"> {0}'
                ' </a>, on branch {1}.'.format(version[0], version[1]))
            self.mw.version_label.setText(
                '<a href=\"https://github.com/Ulm-IQO/qudi/commit/{0}\" style=\"color: cyan;\"> {0}'
                ' </a>, on branch {1}, configured from {2}'
                ''.format(version[0], version[1], self._configuration.file_path))

        self._connect_signals()
        self.keep_settings()
        self.update_config_widget()
        # IPython console widget
        self.start_jupyter_widget()
        # Configure thread widget
        self.mw.threads_widget.setModel(ThreadManager.instance())
        # Configure remotemodules widget
        self._init_remote_modules_widget()
        self.reset_default_layout()
        self.show()

    def on_deactivate(self) -> None:
        """Close window and remove connections """
        self._disconnect_signals()
        self.stop_jupyter_widget()
        self._save_window_geometry(self.mw)
        self.mw.close()

    def _connect_signals(self) -> None:
        get_signal_handler().sigRecordLogged.connect(self.handle_log_record, QtCore.Qt.QueuedConnection)
        qudi_main = self._qudi_main
        # Connect up the main windows actions
        self.mw.action_quit.triggered.connect(qudi_main.prompt_quit, QtCore.Qt.QueuedConnection)
        self.mw.action_load_configuration.triggered.connect(self.load_configuration)
        self.mw.action_reload_qudi.triggered.connect(
            qudi_main.prompt_restart, QtCore.Qt.QueuedConnection)
        self.mw.action_open_configuration_editor.triggered.connect(self.new_configuration)
        self.mw.action_load_all_modules.triggered.connect(
            qudi_main.module_manager.activate_all_modules
        )
        self.mw.action_deactivate_all_modules.triggered.connect(
            qudi_main.module_manager.deactivate_all_modules
        )
        self.mw.action_clear_all_appdata.triggered.connect(
            qudi_main.module_manager.clear_all_appdata
        )
        self.mw.action_view_default.triggered.connect(self.reset_default_layout)
        # Connect signals from manager
        self._configuration.sigConfigChanged.connect(self.update_config_widget)
        # Settings dialog
        self.mw.settings_dialog.accepted.connect(self.apply_settings)
        self.mw.settings_dialog.rejected.connect(self.keep_settings)
        self.error_dialog.disable_checkbox.clicked.connect(self._error_dialog_enabled_changed)
        # Modules list
        self.mw.module_widget.sigActivateModule.connect(qudi_main.module_manager.activate_module)
        self.mw.module_widget.sigReloadModule.connect(qudi_main.module_manager.reload_module)
        self.mw.module_widget.sigDeactivateModule.connect(
            qudi_main.module_manager.deactivate_module
        )
        self.mw.module_widget.sigCleanupModule.connect(
            qudi_main.module_manager.clear_module_appdata
        )

    def _disconnect_signals(self) -> None:
        qudi_main = self._qudi_main
        # Disconnect the main windows actions
        self.mw.action_quit.triggered.disconnect()
        self.mw.action_load_configuration.triggered.disconnect()
        self.mw.action_reload_qudi.triggered.disconnect()
        self.mw.action_open_configuration_editor.triggered.disconnect()
        self.mw.action_load_all_modules.triggered.disconnect()
        self.mw.action_deactivate_all_modules.triggered.disconnect()
        self.mw.action_clear_all_appdata.triggered.disconnect()
        self.mw.action_view_default.triggered.disconnect()
        # Disconnect signals from manager
        self._configuration.sigConfigChanged.disconnect(self.update_config_widget)
        # Settings dialog
        self.mw.settings_dialog.accepted.disconnect()
        self.mw.settings_dialog.rejected.disconnect()
        self.error_dialog.disable_checkbox.clicked.disconnect()
        # Modules list
        self.mw.module_widget.sigActivateModule.disconnect()
        self.mw.module_widget.sigReloadModule.disconnect()
        self.mw.module_widget.sigDeactivateModule.disconnect()
        self.mw.module_widget.sigCleanupModule.disconnect()

        get_signal_handler().sigRecordLogged.disconnect(self.handle_log_record)

    def _init_remote_modules_widget(self) -> None:
        remote_server = self._qudi_main.remote_modules_server
        # hide remote modules menu action if RemoteModuleServer is not available
        if remote_server is None:
            self.mw.remote_widget.setVisible(False)
            self.mw.remote_dockwidget.setVisible(False)
            self.mw.action_view_remote.setVisible(False)
        else:
            host = remote_server.server.host
            port = remote_server.server.port
            self.mw.remote_widget.setVisible(True)
            self.mw.remote_widget.server_label.setText(f'Server URL: rpyc://{host}:{port}/')
            self.mw.remote_widget.shared_module_listview.setModel(
                remote_server.service.shared_modules
            )

    def show(self) -> None:
        """ Show the window and bring it to the top """
        self.mw.show()
        self.mw.activateWindow()
        self.mw.raise_()

    def reset_default_layout(self) -> None:
        """ Return the dockwidget layout and visibility to its default state """
        self.mw.config_dockwidget.setVisible(False)
        self.mw.console_dockwidget.setVisible(self._has_console)
        self.mw.remote_dockwidget.setVisible(False)
        self.mw.threads_dockwidget.setVisible(False)
        self.mw.log_dockwidget.setVisible(True)

        self.mw.config_dockwidget.setFloating(False)
        self.mw.console_dockwidget.setFloating(False)
        self.mw.remote_dockwidget.setFloating(False)
        self.mw.threads_dockwidget.setFloating(False)
        self.mw.log_dockwidget.setFloating(False)

        self.mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.mw.config_dockwidget)
        self.mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.mw.log_dockwidget)
        self.mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.mw.remote_dockwidget)
        self.mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.mw.threads_dockwidget)
        self.mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.mw.console_dockwidget)

        self.mw.action_view_console.setChecked(self._has_console)
        self.mw.action_view_console.setVisible(self._has_console)

    def handle_log_record(self, entry: logging.LogRecord) -> None:
        """ Show an error popup if the log entry is error level and above """
        if entry.levelname in ('error', 'critical'):
            self.error_dialog.new_error(entry)

    def start_jupyter_widget(self) -> None:
        """ Starts a qudi IPython kernel in a separate process and connects it to the console widget
        """
        self._has_console = False
        try:
            # Create and start kernel process
            kernel_manager = QtKernelManager(kernel_name='qudi', autorestart=False)
            # kernel_manager.kernel.gui = 'qt4'
            kernel_manager.start_kernel()

            # create kernel client and connect to console widget
            banner = 'This is an interactive IPython console. A reference to the running qudi ' \
                     'instance can be accessed via "qudi". View the current namespace with dir().\n' \
                     'Go, play.\n'
            self.mw.console_widget.banner = banner
            self.mw.console_widget.font_size = self._console_font_size
            self.mw.console_widget.reset_font()
            self.mw.console_widget.set_default_style(colors='linux')
            kernel_client = kernel_manager.client()
            kernel_client.hb_channel.time_to_dead = 10.0
            kernel_client.hb_channel.kernel_died.connect(self.kernel_died_callback)
            kernel_client.start_channels()
            self.mw.console_widget.kernel_manager = kernel_manager
            self.mw.console_widget.kernel_client = kernel_client
            self._has_console = True
            self.log.info('IPython kernel for qudi main GUI successfully started.')
        except jupyter_client.kernelspec.NoSuchKernel:
            self.log.warning(
                'Qudi IPython kernelspec not installed.\n'
                'IPython console and jupyter notebook integration not available.\n'
                'Run "qudi-install-kernel" from within the qudi Python environment to fix this. '
            )
        except:
            self.log.exception(
                'Exception while trying to start IPython kernel for qudi main GUI. Qudi IPython '
                'console not available.'
            )

    @QtCore.Slot()
    def kernel_died_callback(self) -> None:
        try:
            self.mw.console_widget.kernel_client.stop_channels()
        except:
            pass
        if self._has_console:
            self._has_console = False
            self.log.error(
                'Qudi IPython kernel has unexpectedly died. This can be caused by a corrupt qudi '
                'kernelspec installation. Try to run "qudi-install-kernel" from within the qudi '
                'Python environment and restart qudi.'
            )

    def stop_jupyter_widget(self) -> None:
        """ Stops the qudi IPython kernel process and detaches it from the console widget """
        try:
            self.mw.console_widget.kernel_client.stop_channels()
        except:
            self.log.exception('Exception while trying to shutdown qudi IPython client:')
        try:
            self.mw.console_widget.kernel_manager.shutdown_kernel()
        except:
            self.log.exception('Exception while trying to shutdown qudi IPython kernel:')
        self._has_console = False
        self.log.info('IPython kernel process for qudi main GUI has shut down.')

    def keep_settings(self) -> None:
        """ Write old values into settings dialog """
        self.mw.settings_dialog.font_size_spinbox.setValue(self._console_font_size)
        self.mw.settings_dialog.show_error_popups_checkbox.setChecked(self._show_error_popups)

    def apply_settings(self) -> None:
        """ Apply values from settings dialog """
        # Console font size
        font_size = self.mw.settings_dialog.font_size_spinbox.value()
        self.mw.console_widget.font_size = font_size
        self.mw.console_widget.reset_font()
        self._console_font_size = font_size

        # Error popups
        error_popups = self.mw.settings_dialog.show_error_popups_checkbox.isChecked()
        self.error_dialog.set_enabled(error_popups)
        self._show_error_popups = error_popups

    @QtCore.Slot()
    def _error_dialog_enabled_changed(self) -> None:
        """ Callback for the error dialog disable checkbox """
        self._show_error_popups = self.error_dialog.enabled
        self.mw.settings_dialog.show_error_popups_checkbox.setChecked(self._show_error_popups)

    @QtCore.Slot(object)
    def update_config_widget(self, config: Optional[Configuration] = None) -> None:
        """ Clear and refill the tree widget showing the configuration """
        if config is None:
            config = self._configuration
        self.mw.config_widget.set_config(config.config_map)

    def get_qudi_version(self) -> str:
        """ Try to determine the software version in case the program is in a git repository """
        # Try to get repository information if qudi has been checked out as git repo
        if Repo is not None:
            try:
                repo = Repo(os.path.dirname(get_main_dir()))
                branch = repo.active_branch
                rev = str(repo.head.commit)
                return rev, str(branch)
            except InvalidGitRepositoryError:
                pass
            except:
                self.log.exception('Unexpected error while trying to get git repo:')

        # Try to get qudi.core version number
        try:
            from qudi.core import __version__
            return __version__
        except:
            self.log.exception('Unexpected error while trying to get qudi version:')
        return 'unknown'

    def load_configuration(self) -> None:
        """ Ask the user for a file where the configuration should be loaded from """
        filename = QtWidgets.QFileDialog.getOpenFileName(self.mw,
                                                         'Load Configuration',
                                                         get_default_config_dir(True),
                                                         'Configuration files (*.cfg)')[0]
        if filename:
            reply = QtWidgets.QMessageBox.question(
                self.mw,
                'Restart',
                'Do you want to restart to use the configuration?\n'
                'Choosing "No" will use the selected config file for the next start of Qudi.',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.Cancel:
                return
            self._configuration.set_default_path(filename)
            if reply == QtWidgets.QMessageBox.Yes:
                self._qudi_main.restart()

    def new_configuration(self) -> None:
        """ Prompt the user to open the graphical config editor in a subprocess in order to
        edit/create config files for qudi.
        """
        reply = QtWidgets.QMessageBox.question(
                self.mw,
                'Open Configuration Editor',
                'Do you want open the graphical qudi configuration editor to create or edit qudi '
                'config files?\n',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes
        )
        if reply == QtWidgets.QMessageBox.Yes:
            process = subprocess.Popen(args=[sys.executable, '-m', 'tools.config_editor'],
                                       close_fds=False,
                                       env=os.environ.copy(),
                                       stdin=sys.stdin,
                                       stdout=sys.stdout,
                                       stderr=sys.stderr)
