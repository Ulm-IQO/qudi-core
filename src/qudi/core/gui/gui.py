# -*- coding: utf-8 -*-
"""
.. This file contains models of exponential decay fitting routines for qudi based on the lmfit package.
..
.. Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
.. distribution and on <https://github.com/Ulm-IQO/qudi-core/>
..
.. This file is part of qudi.
..
.. Qudi is free software: you can redistribute it and/or modify it under the terms of
.. the GNU Lesser General Public License as published by the Free Software Foundation,
.. either version 3 of the License, or (at your option) any later version.
..
.. Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
.. without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
.. See the GNU Lesser General Public License for more details.
..
.. You should have received a copy of the GNU Lesser General Public License along with qudi.
.. If not, see <https://www.gnu.org/licenses/>.
"""

import os
import weakref
import platform
from PySide2 import QtCore, QtGui, QtWidgets
from qudi.core.gui.main_gui.main_gui import QudiMainGui
from qudi.core.modulemanager import ModuleManager
from qudi.util.paths import get_artwork_dir
from qudi.core.logger import get_logger

try:
    import pyqtgraph as pg
except ImportError:
    pg = None

logger = get_logger(__name__)


class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    """Tray icon class subclassing QSystemTrayIcon for custom functionality."""

    def __init__(self):
        """
        Tray icon constructor.
        Adds all the appropriate menus and actions.
        """
        super().__init__()
        self._actions = dict()
        self.setIcon(QtWidgets.QApplication.instance().windowIcon())
        self.right_menu = QtWidgets.QMenu('Quit')
        self.left_menu = QtWidgets.QMenu('Manager')

        iconpath = os.path.join(get_artwork_dir(), 'icons')
        self.managericon = QtGui.QIcon()
        self.managericon.addFile(
            os.path.join(iconpath, 'go-home'), QtCore.QSize(16, 16)
        )
        self.managerAction = QtWidgets.QAction(
            self.managericon, 'Manager', self.left_menu
        )

        self.exiticon = QtGui.QIcon()
        self.exiticon.addFile(
            os.path.join(iconpath, 'application-exit'), QtCore.QSize(16, 16)
        )
        self.quitAction = QtWidgets.QAction(self.exiticon, 'Quit', self.right_menu)

        self.restarticon = QtGui.QIcon()
        self.restarticon.addFile(
            os.path.join(iconpath, 'view-refresh'), QtCore.QSize(16, 16)
        )
        self.restartAction = QtWidgets.QAction(
            self.restarticon, 'Restart', self.right_menu
        )

        self.left_menu.addAction(self.managerAction)
        self.left_menu.addSeparator()

        self.right_menu.addAction(self.quitAction)
        self.right_menu.addAction(self.restartAction)
        self.setContextMenu(self.right_menu)

        self.activated.connect(self.handle_activation)

    @QtCore.Slot(QtWidgets.QSystemTrayIcon.ActivationReason)
    def handle_activation(self, reason):
        """
        Click handler.
        This method is called when the tray icon is left-clicked.
        It opens a menu at the position of the left click.

        Parameters
        ----------
        reason :
            Reason that caused the activation.
        """
        if reason == self.Trigger:
            self.left_menu.exec_(QtGui.QCursor.pos())

    def add_action(self, label, callback, icon=None):
        """
        Add an action to the system tray.

        Parameters
        ----------
        label : str
            The label of the action.
        callback : function
            The callback function to be executed when the action is triggered.
        icon : QIcon, optional
            The icon to display for the action. If None, a default icon will be used.
        """
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

    def remove_action(self, label):
        """
        Remove an action from the system tray.

        Parameters
        ----------
        label : str
            The label of the action to remove.
        """
        action = self._actions.pop(label, None)
        if action is not None:
            action.triggered.disconnect()
            self.left_menu.removeAction(action)


class Gui(QtCore.QObject):
    """Set up all necessary GUI elements, like application icons, themes, etc."""

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

    def __init__(
        self, qudi_instance, stylesheet_path=None, theme=None, use_opengl=False
    ):
        if theme is None:
            theme = 'qudiTheme'

        super().__init__()

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
        self._sigBalloonMessage.connect(
            self.balloon_message, QtCore.Qt.QueuedConnection
        )

        self._configure_pyqtgraph(use_opengl)
        self.main_gui_module = QudiMainGui(
            qudi_main_weakref=weakref.ref(qudi_instance), name='qudi_main_gui'
        )
        self.system_tray_icon.managerAction.triggered.connect(
            self.activate_main_gui, QtCore.Qt.QueuedConnection
        )
        self.system_tray_icon.quitAction.triggered.connect(
            qudi_instance.quit, QtCore.Qt.QueuedConnection
        )
        self.system_tray_icon.restartAction.triggered.connect(
            qudi_instance.restart, QtCore.Qt.QueuedConnection
        )
        qudi_instance.module_manager.sigModuleStateChanged.connect(
            self._tray_module_action_changed
        )
        self.show_system_tray_icon()

    @classmethod
    def instance(cls):
        """
        Get the singleton instance of Gui.

        Returns
        -------
        Gui
            The singleton instance of the Gui class.
        """
        if cls._instance is None:
            return None
        return cls._instance()

    @staticmethod
    def _init_app_icon():
        """Set up the Qudi application icon."""
        app_icon = QtGui.QIcon(os.path.join(get_artwork_dir(), 'logo', 'logo-qudi.svg'))
        QtWidgets.QApplication.instance().setWindowIcon(app_icon)

    @staticmethod
    def _configure_pyqtgraph(use_opengl=False):
        """
        Configure pyqtgraph settings.

        Parameters
        ----------
        use_opengl : bool, optional
            If True, enable OpenGL usage in pyqtgraph. Default is False.
        """
        if pg is not None:
            testwidget = QtWidgets.QWidget()
            testwidget.ensurePolished()
            bgcolor = testwidget.palette().color(
                QtGui.QPalette.Normal, testwidget.backgroundRole()
            )
            pg.setConfigOption('background', bgcolor)
            pg.setConfigOption('useOpenGL', use_opengl)

    @staticmethod
    def set_theme(theme):
        """
        Set the icon theme for the Qudi application.

        Parameters
        ----------
        theme : str
            The name of the theme to use.
        """
        themepaths = QtGui.QIcon.themeSearchPaths()
        themepaths.append(os.path.join(get_artwork_dir(), 'icons'))
        QtGui.QIcon.setThemeSearchPaths(themepaths)
        QtGui.QIcon.setThemeName(theme)

    @staticmethod
    def set_style_sheet(stylesheet_path):
        """
        Set the QSS stylesheet for the application.

        Parameters
        ----------
        stylesheet_path : str
            Path to the stylesheet file.
        """
        try:
            if not os.path.exists(stylesheet_path):
                stylesheet_path = os.path.join(
                    get_artwork_dir(), 'styles', stylesheet_path
                )

            with open(stylesheet_path, 'r') as stylesheetfile:
                stylesheet = stylesheetfile.read()

            if stylesheet_path.endswith('qdark.qss'):
                path = os.path.join(os.path.dirname(stylesheet_path), 'qdark').replace(
                    '\\', '/'
                )
                stylesheet = stylesheet.replace('{qdark}', path)

            if platform.system().lower() == 'darwin' and stylesheet_path.endswith(
                'qdark.qss'
            ):
                mac_fix = """
                QDockWidget::title
                {
                    background-color: #31363b;
                    text-align: center;
                    height: 12px;
                }
                """
                stylesheet += mac_fix
            QtWidgets.QApplication.instance().setStyleSheet(stylesheet)
        except:
            logger.exception('Exception while setting qudi stylesheet:')

    @staticmethod
    def close_windows():
        """Close all application windows."""
        QtWidgets.QApplication.instance().closeAllWindows()

    def activate_main_gui(self):
        """Activate and show the main GUI module."""
        if QtCore.QThread.currentThread() is not self.thread():
            QtCore.QMetaObject.invokeMethod(
                self, 'activate_main_gui', QtCore.Qt.BlockingQueuedConnection
            )
            return

        if self.main_gui_module.module_state() != 'deactivated':
            self.main_gui_module.show()
            return

        logger.info('Activating main GUI module...')
        print('> Activating main GUI module...')

        self.main_gui_module.module_state.activate()
        QtWidgets.QApplication.instance().processEvents()

    def deactivate_main_gui(self):
        """Deactivate the main GUI module."""
        if QtCore.QThread.currentThread() is not self.thread():
            QtCore.QMetaObject.invokeMethod(
                self, 'deactivate_main_gui', QtCore.Qt.BlockingQueuedConnection
            )
            return

        if self.main_gui_module.module_state() == 'deactivated':
            return

        self.main_gui_module.module_state.deactivate()
        QtWidgets.QApplication.instance().processEvents()

    def show_system_tray_icon(self):
        """Show the system tray icon."""
        self.system_tray_icon.show()

    def hide_system_tray_icon(self):
        """Hide the system tray icon."""
        self.system_tray_icon.hide()

    def close_system_tray_icon(self):
        """
        Remove the system tray icon.

        Tray icon will be lost until Gui.__init__ is called again.
        """
        self.hide_system_tray_icon()
        self.system_tray_icon.quitAction.triggered.disconnect()
        self.system_tray_icon.restartAction.triggered.disconnect()
        self.system_tray_icon.managerAction.triggered.disconnect()
        self.system_tray_icon = None

    def system_tray_notification_bubble(self, title, message, time=None, icon=None):
        """
        Show a notification balloon message from the system tray icon.

        Parameters
        ----------
        title : str
            The notification title of the balloon.
        message : str
            The message to be shown in the balloon.
        time : float, optional
            The display time of the balloon in seconds. Default is None.
        icon : QIcon, optional
            An icon to be used in the balloon. Default is None, which will use the OS default.
        """
        if icon is None:
            icon = QtGui.QIcon()
        if time is None:
            time = 15
        self.system_tray_icon.showMessage(title, message, icon, int(round(time * 1000)))

    def prompt_shutdown(self, modules_locked=True):
        """
        Display a dialog asking the user to confirm shutdown.

        Parameters
        ----------
        modules_locked : bool, optional
            If True, informs the user that modules are locked. Default is True.

        Returns
        -------
        bool
            True if the user confirms shutdown, otherwise False.
        """
        if modules_locked:
            msg = (
                'Some qudi modules are locked right now.\n'
                'Do you really want to quit and force modules to deactivate?'
            )
        else:
            msg = 'Do you really want to quit?'

        result = QtWidgets.QMessageBox.question(
            self.main_gui_module.mw,
            'Qudi: Quit?',
            msg,
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.No,
        )
        return result == QtWidgets.QMessageBox.Yes

    def prompt_restart(self, modules_locked=True):
        """
        Display a dialog asking the user to confirm restart.

        Parameters
        ----------
        modules_locked : bool, optional
            If True, informs the user that modules are locked. Default is True.

        Returns
        -------
        bool
            True if the user confirms restart, otherwise False.
        """
        if modules_locked:
            msg = (
                'Some qudi modules are locked right now.\n'
                'Do you really want to restart and force modules to deactivate?'
            )
        else:
            msg = 'Do you really want to restart?'

        result = QtWidgets.QMessageBox.question(
            self.main_gui_module.mw,
            'Qudi: Restart?',
            msg,
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.No,
        )
        return result == QtWidgets.QMessageBox.Yes

    @QtCore.Slot(str, str)
    def pop_up_message(self, title, message):
        """
        Display a pop-up dialog window with a message and an OK button.

        Parameters
        ----------
        title : str
            The window title of the dialog.
        message : str
            The message to be shown in the dialog window.
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
        QtWidgets.QMessageBox.information(
            None, title, message, QtWidgets.QMessageBox.Ok
        )
        return

    @QtCore.Slot(str, str, object, object)
    def balloon_message(self, title, message, time=None, icon=None):
        """
        Display a balloon notification from the system tray icon.

        Parameters
        ----------
        title : str
            The notification title of the balloon.
        message : str
            The message to be shown in the balloon.
        time : float, optional
            The lingering time of the balloon in seconds.
        icon : QIcon, optional
            An icon to be used in the balloon. Default is None, which will use OS default.
        """
        if not self.system_tray_icon.supportsMessages():
            logger.warning('{0}:\n{1}'.format(title, message))
            return
        if self.thread() is not QtCore.QThread.currentThread():
            self._sigBalloonMessage.emit(title, message, time, icon)
            return
        self.system_tray_notification_bubble(title, message, time=time, icon=icon)
        return

    @QtCore.Slot(str, str, str)
    def _tray_module_action_changed(self, base, module_name, state):
        """
        Update the system tray icon with actions based on the module state.

        Parameters
        ----------
        base : str
            The base module type (e.g., 'gui').
        module_name : str
            The name of the module.
        state : str
            The state of the module (e.g., 'deactivated').
        """
        if self.system_tray_icon and base == 'gui':
            if state == 'deactivated':
                self.system_tray_icon.remove_action(module_name)
            else:
                mod_manager = ModuleManager.instance()
                try:
                    module_inst = mod_manager[module_name].instance
                except KeyError:
                    return
                self.system_tray_icon.add_action(module_name, module_inst.show)

