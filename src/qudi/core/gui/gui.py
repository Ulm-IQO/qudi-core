# -*- coding: utf-8 -*-
"""
This file contains the Qudi console app class.

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

import os
import weakref
import platform
from PySide2 import QtCore, QtGui, QtWidgets
from typing import Optional, Union, Tuple, Iterable, Callable, Dict

try:
    import pyqtgraph as pg
except ImportError:
    pg = None

from qudi.core.logger import get_logger
from qudi.core.modulemanager import ModuleManager
from qudi.core.module import ModuleState, ModuleBase
from qudi.core.gui.main_gui.main_gui import QudiMainGui
from qudi.util.paths import get_artwork_dir
from qudi.util.helpers import current_is_native_thread, call_slot_from_native_thread


logger = get_logger(__name__)


class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    """Tray icon class subclassing QSystemTrayIcon for custom functionality.
    """

    def __init__(self):
        """ Tray icon constructor. Adds all the appropriate menus and actions. """
        super().__init__()
        self._actions: Dict[str, QtWidgets.QAction] = dict()
        self.setIcon(QtWidgets.QApplication.instance().windowIcon())
        self.right_menu = QtWidgets.QMenu('Quit')
        self.left_menu = QtWidgets.QMenu('Manager')

        iconpath = os.path.join(get_artwork_dir(), 'icons')
        self.managericon = QtGui.QIcon()
        self.managericon.addFile(os.path.join(iconpath, 'go-home'), QtCore.QSize(16, 16))
        self.managerAction = QtWidgets.QAction(self.managericon, 'Manager', self.left_menu)

        self.exiticon = QtGui.QIcon()
        self.exiticon.addFile(os.path.join(iconpath, 'application-exit'), QtCore.QSize(16, 16))
        self.quitAction = QtWidgets.QAction(self.exiticon, 'Quit', self.right_menu)

        self.restarticon = QtGui.QIcon()
        self.restarticon.addFile(os.path.join(iconpath, 'view-refresh'), QtCore.QSize(16, 16))
        self.restartAction = QtWidgets.QAction(self.restarticon, 'Restart', self.right_menu)

        self.left_menu.addAction(self.managerAction)
        self.left_menu.addSeparator()

        self.right_menu.addAction(self.quitAction)
        self.right_menu.addAction(self.restartAction)
        self.setContextMenu(self.right_menu)

        self.activated.connect(self.handle_activation)

    @QtCore.Slot(QtWidgets.QSystemTrayIcon.ActivationReason)
    def handle_activation(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason) -> None:
        """ Click handler.
        This method is called when the tray icon is left-clicked.
        It opens a menu at the position of the left click.
        """
        if reason == self.Trigger:
            self.left_menu.exec_(QtGui.QCursor.pos())

    def add_action(self, label: str, callback: Callable[[], None], icon=None) -> None:
        if label in self._actions:
            raise ValueError(f'Action "{label}" already exists in system tray.')

        if not isinstance(icon, QtGui.QIcon):
            icon = QtGui.QIcon()
            iconpath = os.path.join(get_artwork_dir(), 'icons')
            icon.addFile(os.path.join(iconpath, 'go-next'))

        action = QtWidgets.QAction(label)
        action.setIcon(icon)
        action.triggered.connect(callback)
        self.left_menu.addAction(action)
        self._actions[label] = action

    def remove_action(self, label: str) -> None:
        action = self._actions.pop(label, None)
        if action is not None:
            action.triggered.disconnect()
            self.left_menu.removeAction(action)

    def clear_actions(self) -> None:
        for label in list(self._actions):
            self.remove_action(label)


class _ModuleListProxyModel(QtCore.QSortFilterProxyModel):
    """ Model proxy that filters all modules for ModuleBase.GUI type and collapses the table model
    to a list of data tuples
    """
    def columnCount(self, parent: Optional[QtCore.QModelIndex] = None) -> int:
        return 1

    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:
        return self.sourceModel().index(source_row, 0, source_parent).data() == ModuleBase.GUI

    def data(self,
             index: QtCore.QModelIndex,
             role: Optional[QtCore.Qt.ItemDataRole] = QtCore.Qt.DisplayRole
             ) -> Union[None, Tuple[str, ModuleState]]:
        if index.isValid() and (role == QtCore.Qt.DisplayRole):
            source_index = self.mapToSource(index)
            module = source_index.data(QtCore.Qt.UserRole)
            return module.name, module.state
        return None


class Gui(QtCore.QObject):
    """ Set up all necessary GUI elements, like application icons, themes, etc. """
    _instance = None

    _sigPopUpMessage = QtCore.Signal(str, str)
    _sigBalloonMessage = QtCore.Signal(str, str, object, object)

    def __new__(cls, *args, **kwargs):
        if cls._instance is None or cls._instance() is None:
            obj = super().__new__(cls, *args, **kwargs)
            cls._instance = weakref.ref(obj)
            return obj
        raise RuntimeError(
            'Gui is a singleton. Please use Gui.instance() to get a reference to the already '
            'created instance.'
        )

    def __init__(self,
                 qudi_instance: 'Qudi',
                 stylesheet_path: Optional[str] = None,
                 theme: Optional[str] = 'qudiTheme',
                 use_opengl: Optional[bool] = False,
                 parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

        app = QtWidgets.QApplication.instance()
        if app is None:
            raise RuntimeError('No Qt GUI app running (no QApplication instance).')
        app.setQuitOnLastWindowClosed(False)

        self._init_app_icon()
        self.set_theme(theme)
        if stylesheet_path is not None:
            self.set_style_sheet(stylesheet_path)
        self.system_tray_icon = SystemTrayIcon()

        self._sigPopUpMessage.connect(self.pop_up_message, QtCore.Qt.QueuedConnection)
        self._sigBalloonMessage.connect(self.balloon_message, QtCore.Qt.QueuedConnection)

        self._configure_pyqtgraph(use_opengl)
        self.main_gui_module = QudiMainGui(qudi_main=qudi_instance, name='qudi_main_gui')
        self.system_tray_icon.managerAction.triggered.connect(self.activate_main_gui,
                                                              QtCore.Qt.QueuedConnection)
        self.system_tray_icon.quitAction.triggered.connect(qudi_instance.quit,
                                                           QtCore.Qt.QueuedConnection)
        self.system_tray_icon.restartAction.triggered.connect(qudi_instance.restart,
                                                              QtCore.Qt.QueuedConnection)
        self._module_manager: ModuleManager = qudi_instance.module_manager
        self._modules_list_proxy = _ModuleListProxyModel()
        self._modules_list_proxy.setSourceModel(self._module_manager)
        self._modules_list_proxy.modelReset.connect(self._reset_tray_modules)
        self._modules_list_proxy.rowsInserted.connect(self._reset_tray_modules)
        self._modules_list_proxy.rowsRemoved.connect(self._reset_tray_modules)
        self._modules_list_proxy.dataChanged.connect(self._tray_module_changed)
        self._reset_tray_modules()
        self.system_tray_icon.show()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            return None
        return cls._instance()

    @staticmethod
    def _init_app_icon() -> None:
        """ Set up the Qudi application icon """
        app_icon = QtGui.QIcon(os.path.join(get_artwork_dir(), 'logo', 'logo-qudi.svg'))
        QtWidgets.QApplication.instance().setWindowIcon(app_icon)

    @staticmethod
    def _configure_pyqtgraph(use_opengl: Optional[bool] = False) -> None:
        """ Configure pyqtgraph (if present) """
        if pg is not None:
            # test setting background of pyqtgraph
            testwidget = QtWidgets.QWidget()
            testwidget.ensurePolished()
            bgcolor = testwidget.palette().color(QtGui.QPalette.Normal, testwidget.backgroundRole())
            # set manually the background color in hex code according to our color scheme:
            pg.setConfigOption('background', bgcolor)
            # experimental opengl usage
            pg.setConfigOption('useOpenGL', use_opengl)

    @staticmethod
    def set_theme(theme: str) -> None:
        """ Set icon theme for qudi app """
        # Make icons work on non-X11 platforms, set custom theme
        # if not sys.platform.startswith('linux') and not sys.platform.startswith('freebsd'):
        #
        # To enable the use of custom action icons, for now the above if statement has been
        # removed and the QT theme is being set to our artwork/icons folder for
        # all OSs.
        themepaths = QtGui.QIcon.themeSearchPaths()
        themepaths.append(os.path.join(get_artwork_dir(), 'icons'))
        QtGui.QIcon.setThemeSearchPaths(themepaths)
        QtGui.QIcon.setThemeName(theme)

    @staticmethod
    def set_style_sheet(stylesheet_path: str) -> None:
        """ Set qss style sheet for application """
        try:
            if not os.path.exists(stylesheet_path):
                stylesheet_path = os.path.join(get_artwork_dir(), 'styles', stylesheet_path)

            with open(stylesheet_path, 'r') as stylesheetfile:
                stylesheet = stylesheetfile.read()

            if stylesheet_path.endswith('qdark.qss'):
                path = os.path.join(os.path.dirname(stylesheet_path), 'qdark').replace('\\', '/')
                stylesheet = stylesheet.replace('{qdark}', path)

            # see issue #12 on qdarkstyle github
            if platform.system().lower() == 'darwin' and stylesheet_path.endswith('qdark.qss'):
                mac_fix = '''
                QDockWidget::title
                {
                    background-color: #31363b;
                    text-align: center;
                    height: 12px;
                }
                '''
                stylesheet += mac_fix
            QtWidgets.QApplication.instance().setStyleSheet(stylesheet)
        except:
            logger.exception('Exception while setting qudi stylesheet:')

    @staticmethod
    def close_windows() -> None:
        """ Close all application windows """
        QtWidgets.QApplication.instance().closeAllWindows()

    def activate_main_gui(self) -> None:
        if not current_is_native_thread(self):
            call_slot_from_native_thread(self, 'activate_main_gui', blocking=True)
            return

        if self.main_gui_module.module_state.current.deactivated:
            logger.info('Activating main GUI module...')
            print('> Activating main GUI module...')

            self.main_gui_module.module_state.activate()
            QtWidgets.QApplication.instance().processEvents()
        else:
            self.main_gui_module.show()

    def deactivate_main_gui(self) -> None:
        if not current_is_native_thread(self):
            call_slot_from_native_thread(self, 'deactivate_main_gui', blocking=True)
            return

        if not self.main_gui_module.module_state.current.deactivated:
            self.main_gui_module.module_state.deactivate()

    def close_system_tray_icon(self) -> None:
        """ Kill and delete system tray icon.
        Tray icon will be lost until Gui.__init__ is called again.
        """
        self.system_tray_icon.hide()
        self.system_tray_icon.quitAction.triggered.disconnect()
        self.system_tray_icon.restartAction.triggered.disconnect()
        self.system_tray_icon.managerAction.triggered.disconnect()
        self.system_tray_icon = None

    def system_tray_notification_bubble(self,
                                        title: str,
                                        message: str,
                                        time: Optional[float] = None,
                                        icon: Optional[QtGui.QIcon] = None) -> None:
        """ Helper method to invoke balloon messages in the system tray by calling
        QSystemTrayIcon.showMessage.

        @param str title: The notification title of the balloon
        @param str message: The message to be shown in the balloon
        @param float time: optional, The lingering time of the balloon in seconds
        @param QIcon icon: optional, an icon to be used in the balloon. "None" will use OS default.
        """
        if icon is None:
            icon = QtGui.QIcon()
        if time is None:
            time = 15
        self.system_tray_icon.showMessage(title, message, icon, int(round(time * 1000)))

    def prompt_shutdown(self, modules_locked: Optional[bool] = True) -> bool:
        """ Display a dialog, asking the user to confirm shutdown """
        if modules_locked:
            msg = 'Some qudi modules are locked right now.\n' \
                  'Do you really want to quit and force modules to deactivate?'
        else:
            msg = 'Do you really want to quit?'

        result = QtWidgets.QMessageBox.question(self.main_gui_module.mw,
                                                'Qudi: Quit?',
                                                msg,
                                                QtWidgets.QMessageBox.Yes,
                                                QtWidgets.QMessageBox.No)
        return result == QtWidgets.QMessageBox.Yes

    def prompt_restart(self, modules_locked: Optional[bool] = True) -> bool:
        """ Display a dialog, asking the user to confirm restart """
        if modules_locked:
            msg = 'Some qudi modules are locked right now.\n' \
                  'Do you really want to restart and force modules to deactivate?'
        else:
            msg = 'Do you really want to restart?'

        result = QtWidgets.QMessageBox.question(self.main_gui_module.mw,
                                                'Qudi: Restart?',
                                                msg,
                                                QtWidgets.QMessageBox.Yes,
                                                QtWidgets.QMessageBox.No)
        return result == QtWidgets.QMessageBox.Yes

    @QtCore.Slot(str, str)
    def pop_up_message(self, title: str, message: str) -> None:
        """ Slot prompting a dialog window with a message and an OK button to dismiss it.

        @param str title: The window title of the dialog
        @param str message: The message to be shown in the dialog window
        """
        if not isinstance(title, str):
            logger.error('pop-up message title must be str type')
            return
        if not isinstance(message, str):
            logger.error('pop-up message must be str type')
            return
        if self.thread() is not QtCore.QThread.currentThread():
            self._sigPopUpMessage.emit(title, message)
            return
        QtWidgets.QMessageBox.information(None, title, message, QtWidgets.QMessageBox.Ok)

    @QtCore.Slot(str, str, object, object)
    def balloon_message(self,
                        title: str,
                        message: str,
                        time: Optional[float] = None,
                        icon: Optional[QtGui.QIcon] = None) -> None:
        """ Slot prompting a balloon notification from the system tray icon.

        @param str title: The notification title of the balloon
        @param str message: The message to be shown in the balloon
        @param float time: optional, The lingering time of the balloon in seconds
        @param QIcon icon: optional, an icon to be used in the balloon. "None" will use OS default.
        """
        if not self.system_tray_icon.supportsMessages():
            logger.warning(f'{title}:\n{message}')
            return
        if self.thread() is not QtCore.QThread.currentThread():
            self._sigBalloonMessage.emit(title, message, time, icon)
            return
        self.system_tray_notification_bubble(title, message, time=time, icon=icon)

    @QtCore.Slot()
    def _reset_tray_modules(self) -> None:
        if self.system_tray_icon is not None:
            self.system_tray_icon.clear_actions()
            module_states = [
                self._modules_list_proxy.index(row, 0).data() for row in
                range(self._modules_list_proxy.rowCount())
            ]
            for name, state in module_states:
                if not state.deactivated:
                    self.system_tray_icon.add_action(
                        name,
                        lambda: self._module_manager.activate_module(name)
                    )

    @QtCore.Slot(QtCore.QModelIndex, QtCore.QModelIndex, object)
    def _tray_module_changed(self,
                             top_left: QtCore.QModelIndex,
                             bottom_right: QtCore.QModelIndex,
                             roles: Iterable[QtCore.Qt.ItemDataRole]) -> None:
        for row in range(top_left.row(), bottom_right.row() + 1):
            name, state = top_left.model().index(row, 0).data()
            if state.deactivated:
                self.system_tray_icon.remove_action(name)
            else:
                try:
                    self.system_tray_icon.add_action(
                        name,
                        lambda: self._module_manager.activate_module(name)
                    )
                except ValueError:
                    pass
