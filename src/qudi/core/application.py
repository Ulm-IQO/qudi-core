# -*- coding: utf-8 -*-
"""
This file contains the qudi Manager class.

Copyright (c) 2021-2024, the qudi developers. See the AUTHORS.md file at the top-level directory of this
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

import gc
import sys
import os
import weakref
import inspect
import warnings
import traceback
import faulthandler
from logging import DEBUG, INFO, Logger
from PySide2 import QtCore, QtWidgets, QtGui
from typing import Optional, Union, Dict, Callable, Tuple, Iterable, List

from qudi.core.logger import init_rotating_file_handler, init_record_model_handler, clear_handlers
from qudi.core.logger import get_logger, set_log_level
from qudi.util.paths import get_default_log_dir, get_artwork_dir
from qudi.util.mutex import Mutex
from qudi.util.colordefs import QudiMatplotlibStyle
from qudi.core.config import Configuration, ValidationError, YAMLError
from qudi.core.watchdog import AppWatchdog
from qudi.core.module import ModuleState, ModuleBase
from qudi.core.modulemanager import ModuleManager
from qudi.core.threadmanager import ThreadManager
from qudi.core.gui import configure_pyqtgraph, initialize_app_icon, set_theme, set_stylesheet
from qudi.core.gui import close_windows, prompt_restart, prompt_shutdown
from qudi.core.servers import RemoteModulesServer, QudiNamespaceServer


def setup_environment() -> None:
    # Set QT_API environment variable to PySide2
    os.environ['QT_API'] = 'pyside2'

    # Enable the High DPI scaling support of Qt5
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'

    if sys.platform == 'win32':
        # Set QT_LOGGING_RULES environment variable to suppress qt.svg related warnings that
        # otherwise spam the log due to some known Qt5 bugs,
        # e.g. https://bugreports.qt.io/browse/QTBUG-52079
        os.environ['QT_LOGGING_RULES'] = 'qt.svg.warning=false'
    else:
        # The following will prevent Qt to spam the logs on X11 systems with enough messages
        # to significantly slow the program down. Most of those warnings should have been
        # notice level or lower. This is a known problem since Qt does not fully comply to X11.
        os.environ['QT_LOGGING_RULES'] = '*.debug=false;*.info=false;*.notice=false;*.warning=false'


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


class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    """ QSystemTrayIcon for graphical qudi application """
    def __init__(self,
                 module_manager: ModuleManager,
                 quit_callback: Callable[[], None],
                 restart_callback: Callable[[], None],
                 parent: Optional[QtCore.QObject] = None):
        """ Tray icon constructor. Adds all the appropriate menus and actions. """
        super().__init__(icon=QtWidgets.QApplication.instance().windowIcon(), parent=parent)

        self._module_manager = module_manager
        self._module_actions: Dict[str, QtWidgets.QAction] = dict()
        self._right_menu = QtWidgets.QMenu('Menu')
        self._left_menu = QtWidgets.QMenu('Modules')

        iconpath = os.path.join(get_artwork_dir(), 'icons')

        icon = QtGui.QIcon()
        icon.addFile(os.path.join(iconpath, 'application-exit'), QtCore.QSize(16, 16))
        self._quit_action = QtWidgets.QAction(icon, 'Quit', self._right_menu)
        self._quit_action.triggered.connect(quit_callback, QtCore.Qt.QueuedConnection)
        self._right_menu.addAction(self._quit_action)
        icon = QtGui.QIcon()
        icon.addFile(os.path.join(iconpath, 'view-refresh'), QtCore.QSize(16, 16))
        self._restart_action = QtWidgets.QAction(icon, 'Restart', self._right_menu)
        self._restart_action.triggered.connect(restart_callback, QtCore.Qt.QueuedConnection)
        self._right_menu.addAction(self._restart_action)
        if self._module_manager.has_main_gui:
            icon = QtGui.QIcon()
            icon.addFile(os.path.join(iconpath, 'go-home'), QtCore.QSize(16, 16))
            self._main_gui_action = QtWidgets.QAction(icon, 'Main GUI', self._left_menu)
            self._main_gui_action.triggered.connect(
                self._module_manager.activate_main_gui,
                QtCore.Qt.QueuedConnection
            )
            self._left_menu.addAction(self._main_gui_action)
            self._left_menu.addSeparator()

        self.setContextMenu(self._right_menu)
        self.activated.connect(self._handle_activation)

        self._model_proxy = _ModuleListProxyModel(parent=self)
        self._model_proxy.setSourceModel(module_manager)
        self._model_proxy.modelReset.connect(self.__reset_modules)
        self._model_proxy.rowsInserted.connect(self.__reset_modules)
        self._model_proxy.rowsRemoved.connect(self.__reset_modules)
        self._model_proxy.dataChanged.connect(self.__module_states_changed)
        self.__reset_modules()

    @QtCore.Slot(str, str, object, object)
    def notification_bubble(self,
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
        if self.supportsMessages():
            if icon is None:
                icon = QtGui.QIcon()
            if time is None:
                time = 10
            self.showMessage(title, message, icon, int(round(time * 1000)))
        else:
            get_logger('pop-up message').warning(f'{title}:\n{message}')

    @QtCore.Slot(QtWidgets.QSystemTrayIcon.ActivationReason)
    def _handle_activation(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason) -> None:
        """ This method is called when the tray icon is left-clicked. It opens a menu at the
        position of the click.
        """
        if reason == self.Trigger:
            self._left_menu.exec_(QtGui.QCursor.pos())

    def _add_module_action(self, name: str) -> None:
        if name not in self._module_actions:
            icon = QtGui.QIcon()
            iconpath = os.path.join(get_artwork_dir(), 'icons')
            icon.addFile(os.path.join(iconpath, 'go-next'))
            action = QtWidgets.QAction(icon=icon, text=name)
            action.triggered.connect(lambda: self._module_manager.activate_module(name))
            self._left_menu.addAction(action)
            self._module_actions[name] = action

    def _remove_module_action(self, name: str) -> None:
        action = self._module_actions.pop(name, None)
        if action is not None:
            action.triggered.disconnect()
            self._left_menu.removeAction(action)

    def _clear_module_actions(self) -> None:
        for label in list(self._module_actions):
            self._remove_module_action(label)

    @QtCore.Slot()
    def __reset_modules(self) -> None:
        self._clear_module_actions()
        module_states = [
            self._model_proxy.index(row, 0).data() for row in range(self._model_proxy.rowCount())
        ]
        for name, state in module_states:
            if not state.deactivated:
                self._add_module_action(name)

    @QtCore.Slot(QtCore.QModelIndex, QtCore.QModelIndex, object)
    def __module_states_changed(self,
                               top_left: QtCore.QModelIndex,
                               bottom_right: QtCore.QModelIndex,
                               roles: Iterable[QtCore.Qt.ItemDataRole]) -> None:
        model = top_left.model()
        for row in range(top_left.row(), bottom_right.row() + 1):
            name, state = model.index(row, 0).data()
            if state.deactivated:
                self._remove_module_action(name)
            else:
                self._add_module_action(name)


class Qudi(QtCore.QObject):
    """ The main runtime singleton for qudi.
    Sets up everything and calling "run" starts the application.
    """
    _instance = None
    _run_lock = Mutex()
    _quit_lock = Mutex()

    no_gui: bool
    debug_mode: bool
    log_dir: str
    log: Logger
    configuration: Configuration
    thread_manager: ThreadManager
    module_manager: ModuleManager
    remote_modules_server: Union[RemoteModulesServer, None]
    local_namespace_server: QudiNamespaceServer
    watchdog: Union[AppWatchdog, None]
    tray_icon: Union[SystemTrayIcon, None]
    _configured_extension_paths: List[str]
    _is_running: bool
    _shutting_down: bool

    def __new__(cls, *args, **kwargs):
        if cls._instance is None or cls._instance() is None:
            obj = super().__new__(cls, *args, **kwargs)
            cls._instance = weakref.ref(obj)
            return obj
        raise RuntimeError(
            'Only one qudi instance per process possible (Singleton). Please use '
            'Qudi.instance() to get a reference to the already created instance.'
        )

    def __init__(self,
                 no_gui: Optional[bool] = False,
                 debug: Optional[bool] = False,
                 log_dir: Optional[str] = '',
                 config_file: Optional[str] = None,
                 parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

        # CLI arguments
        self.no_gui = bool(no_gui)
        self.debug_mode = bool(debug)
        self.log_dir = str(log_dir) if os.path.isdir(log_dir) else get_default_log_dir(
            create_missing=True
        )

        # Enable stack trace output for SIGSEGV, SIGFPE, SIGABRT, SIGBUS and SIGILL signals
        # -> e.g. for segmentation faults
        faulthandler.disable()
        faulthandler.enable(all_threads=True)

        # install logging facility and set logging level
        init_record_model_handler(max_records=10000)
        init_rotating_file_handler(path=self.log_dir)
        set_log_level(DEBUG if self.debug_mode else INFO)
        # Enable all warnings when in debug mode (especially DeprecationWarnings)
        if self.debug_mode:
            warnings.simplefilter('always')

        # Set up logger for qudi main instance
        self.log = get_logger(__class__.__name__)  # "qudi.Qudi" in custom logger
        sys.excepthook = self._qudi_excepthook

        # Load configuration from disc if possible
        self.configuration = Configuration()
        try:
            self.configuration.load(config_file, set_default=True)
        except ValueError:
            self.log.info('No qudi configuration file specified. Using empty default config.')
        except (ValidationError, YAMLError):
            self.log.exception('Invalid qudi configuration file specified. '
                               'Falling back to default config.')

        # initialize thread manager and module manager
        self.thread_manager = ThreadManager(parent=self)
        self.module_manager = ModuleManager(qudi_main=self, parent=self)

        # initialize remote modules server if needed
        remote_server_config = self.configuration['remote_modules_server']
        if remote_server_config:
            self.remote_modules_server = RemoteModulesServer(
                parent=self,
                module_manager=self.module_manager,
                thread_manager=self.thread_manager,
                name='remote-modules-server',
                host=remote_server_config.get('address', None),
                port=remote_server_config.get('port', None),
                certfile=remote_server_config.get('certfile', None),
                keyfile=remote_server_config.get('certfile', None),
                protocol_config=remote_server_config.get('protocol_config', None),
                ssl_version=remote_server_config.get('ssl_version', None),
                cert_reqs=remote_server_config.get('cert_reqs', None),
                ciphers=remote_server_config.get('ciphers', None),
                force_remote_calls_by_value=self.configuration['force_remote_calls_by_value']
            )
        else:
            self.remote_modules_server = None
        self.local_namespace_server = QudiNamespaceServer(
            parent=self,
            qudi=self,
            name='local-namespace-server',
            port=self.configuration['namespace_server_port'],
            force_remote_calls_by_value=self.configuration['force_remote_calls_by_value']
        )
        self.watchdog = None
        self.tray_icon = None

        self._configured_extension_paths = list()
        self._is_running = False
        self._shutting_down = False

    def _qudi_excepthook(self, ex_type, ex_value, ex_traceback):
        """ Handler function to be used as sys.excepthook. Should forward all unhandled exceptions
        to logging module.
        """
        # Use default sys.excepthook if exception is exotic/no subclass of Exception.
        if not issubclass(ex_type, Exception):
            sys.__excepthook__(ex_type, ex_value, ex_traceback)
            return

        # Get the most recent traceback
        most_recent_frame = None
        for most_recent_frame, _ in traceback.walk_tb(ex_traceback):
            pass
        # Try to extract the module and class name in which the exception has been raised
        msg = ''
        if most_recent_frame is None:
            logger = self.log
            msg = 'Unhandled qudi exception:'
        else:
            try:
                obj = most_recent_frame.f_locals['self']
                logger = get_logger(f'{obj.__module__}.{obj.__class__.__name__}')
            except (KeyError, AttributeError):
                # Try to extract just the module name in which the exception has been raised
                try:
                    mod = inspect.getmodule(most_recent_frame.f_code)
                    logger = get_logger(mod.__name__)
                except AttributeError:
                    # If no module and class name can be determined, use the application logger
                    logger = self.log
                    msg = 'Unhandled qudi exception:'
        # Log exception with qudi log handler
        logger.error(msg, exc_info=(ex_type, ex_value, ex_traceback))

    @classmethod
    def instance(cls):
        if cls._instance is None:
            return None
        return cls._instance()

    @property
    def is_running(self) -> bool:
        return self._is_running

    def _remove_extensions_from_path(self) -> None:
        # Clean up previously configured expansion paths
        for ext_path in self._configured_extension_paths:
            try:
                sys.path.remove(ext_path)
            except ValueError:
                pass

    def _add_extensions_to_path(self) -> None:
        extensions = self.configuration['extension_paths']
        # Add qudi extension paths to sys.path
        insert_index = 1
        for ext_path in reversed(extensions):
            sys.path.insert(insert_index, ext_path)
        self._configured_extension_paths = extensions

    def _configure_qudi_modules(self) -> None:
        """
        """
        if self.configuration.file_path is None:
            print('> Applying default configuration...')
            self.log.info('Applying default configuration...')
        else:
            print(f'> Applying configuration from "{self.configuration.file_path}"...')
            self.log.info(f'Applying configuration from "{self.configuration.file_path}"...')

        # Clear all qudi modules
        self.module_manager.clear()

        # Configure extension paths
        self._remove_extensions_from_path()
        self._add_extensions_to_path()

        # Configure qudi modules
        main_gui_cfg = self.configuration['main_gui']
        if main_gui_cfg is not None:
            self.module_manager.set_main_gui(main_gui_cfg)
        for base in ModuleBase:
            # Create ManagedModule instance by adding each module to ModuleManager
            for module_name, module_cfg in self.configuration[base.value].items():
                try:
                    self.module_manager.add_module(name=module_name,
                                                   base=base,
                                                   configuration=module_cfg)
                except:
                    self.module_manager.remove_module(module_name, ignore_missing=True)
                    self.log.exception(f'Unable to create ManagedModule instance for {base} '
                                       f'module "{module_name}"')

        print('> Qudi configuration complete!')
        self.log.info('Qudi configuration complete!')

    def _start_gui(self) -> None:
        app = QtWidgets.QApplication.instance()
        if app is None:
            raise RuntimeError('No Qt GUI app running (no QApplication instance).')

        # Configure App for GUI mode
        app.setQuitOnLastWindowClosed(False)
        initialize_app_icon()
        set_theme()
        set_stylesheet(self.configuration['stylesheet'])
        configure_pyqtgraph()
        # Create system tray icon
        self.tray_icon = SystemTrayIcon(module_manager=self.module_manager,
                                        quit_callback=self.quit,
                                        restart_callback=self.restart,
                                        parent=None)
        self.tray_icon.show()
        # Start main GUI
        if self.module_manager.has_main_gui:
            self.module_manager.activate_main_gui()

    def _stop_gui(self) -> None:
        try:
            if self.module_manager.has_main_gui:
                self.module_manager.deactivate_main_gui()
        finally:
            self.tray_icon.hide()
            self.tray_icon = None
            self.log.info('Closing remaining windows...')
            print('> Closing remaining windows...')
            close_windows()

    def _start_startup_modules(self):
        startup_modules = self.configuration['startup_modules']
        if startup_modules:
            print(f'> Loading startup modules')
            self.log.info(f'Loading startup modules')
            for module in startup_modules:
                # Do not crash if a module can not be started
                try:
                    self.module_manager.activate_module(module)
                except:
                    self.log.exception(f'Unable to activate startup module "{module}":')

    def run(self):
        """ Configures qudi runtime components and starts the Qt event loop. Runs indefinitely
        until QtCore.QCoreApplication.exit() is called, e.g. via calling quit().
        """
        with self._run_lock:
            if self._is_running:
                raise RuntimeError('Qudi is already running!')

            # Notify startup
            startup_info = f'Starting qudi{" in debug mode..." if self.debug_mode else "..."}'
            self.log.info(startup_info)
            print(f'> {startup_info}')

            setup_environment()

            # Set default Qt locale to "C" in order to avoid surprises with number formats and
            # other things
            # QtCore.QLocale.setDefault(QtCore.QLocale('en_US'))
            QtCore.QLocale.setDefault(QtCore.QLocale.c())

            # Use non-GUI "Agg" backend for matplotlib by default since it is reasonably
            # thread-safe. Otherwise you can only plot from main thread and not e.g. in a logic
            # module. This causes qudi to not be able to spawn matplotlib GUIs e.g. by calling
            # matplotlib.pyplot.show()
            try:
                import matplotlib as _mpl
                _mpl.use('Agg')
            except ImportError:
                pass

            # Set qudi style for matplotlib
            try:
                import matplotlib.pyplot as plt
                plt.style.use(QudiMatplotlibStyle.style)
            except ImportError:
                pass

            # Get QApplication instance
            app_cls = QtCore.QCoreApplication if self.no_gui else QtWidgets.QApplication
            app = app_cls.instance()
            if app is None:
                app = app_cls(sys.argv)

            # Install app watchdog
            self.watchdog = AppWatchdog(self.interrupt_quit)

            # Apply module configuration
            self._configure_qudi_modules()

            # Start module servers
            if self.remote_modules_server is not None:
                self.remote_modules_server.start()
            self.local_namespace_server.start()

            # Configure GUI framework if needed
            if not self.no_gui:
                self._start_gui()

            # Start the autostart modules defined in the config file
            self._start_startup_modules()

            # Start Qt event loop unless running in interactive mode
            self._is_running = True
            self.log.info('Initialization complete! Starting Qt event loop...')
            print('> Initialization complete! Starting Qt event loop...\n>')
            exit_code = app.exec_()

            self._shutting_down = False
            self._is_running = False
            self.log.info('Shutdown complete! Ciao')
            print('>\n>   Shutdown complete! Ciao.\n>')

            # Exit application
            sys.exit(exit_code)

    def _exit(self, prompt=True, restart=False):
        """ Shutdown qudi. Nicely request that all modules shut down if prompt is True.
        Signal restart to parent process (if present) via exitcode 42 if restart is True.
        """
        with self._quit_lock:
            if not self.is_running or self._shutting_down:
                return
            self._shutting_down = True
            if prompt:
                locked_modules = False
                for row in range(self.module_manager.rowCount()):
                    if self.module_manager.index(row, 2).data().locked:
                        locked_modules = True
                        break

                if self.no_gui:
                    # command line prompt
                    question = '\nSome modules are still locked. ' if locked_modules else '\n'
                    if restart:
                        question += 'Do you really want to restart qudi (y/N)?: '
                    else:
                        question += 'Do you really want to quit qudi (y/N)?: '
                    while True:
                        response = input(question).lower()
                        if response in ('y', 'yes'):
                            break
                        elif response in ('', 'n', 'no'):
                            self._shutting_down = False
                            return
                else:
                    # GUI prompt
                    if self.module_manager.has_main_gui:
                        instance = self.module_manager.get_main_gui_instance()
                        # ToDo: Get QMainWindow instance from GuiBase instance
                        parent = None
                    else:
                        parent = None
                    if restart:
                        if not prompt_restart(locked_modules, parent):
                            self._shutting_down = False
                            return
                    else:
                        if not prompt_shutdown(locked_modules, parent):
                            self._shutting_down = False
                            return

            QtCore.QCoreApplication.instance().processEvents()
            self.log.info('Qudi shutting down...')
            print('> Qudi shutting down...')
            self.watchdog.terminate()
            self.watchdog = None
            self.log.info('Stopping module server(s)...')
            print('> Stopping module server(s)...')
            if self.remote_modules_server is not None:
                try:
                    self.remote_modules_server.stop()
                except:
                    self.log.exception('Exception during shutdown of remote modules server:')
            try:
                self.local_namespace_server.stop()
            except:
                self.log.exception('Error during shutdown of local namespace server:')
            QtCore.QCoreApplication.instance().processEvents()
            self.log.info('Deactivating modules...')
            print('> Deactivating modules...')
            self.module_manager.clear()
            QtCore.QCoreApplication.instance().processEvents()
            if not self.no_gui:
                self._stop_gui()
                QtCore.QCoreApplication.instance().processEvents()
            self.log.info('Stopping remaining threads...')
            print('> Stopping remaining threads...')
            self.thread_manager.quit_all_threads()
            QtCore.QCoreApplication.instance().processEvents()
            clear_handlers()
            # FIXME: Suppress ResourceWarning from jupyter_client package upon garbage collection.
            #  This is just sloppy implementation from jupyter and not critical.
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=ResourceWarning, module='asyncio')
                # Explicit gc call to prevent Qt C++ extensions from using deleted Python objects
                gc.collect()
            if restart:
                QtCore.QCoreApplication.exit(42)
            else:
                QtCore.QCoreApplication.quit()

    @QtCore.Slot()
    def quit(self):
        self._exit(prompt=False, restart=False)

    @QtCore.Slot()
    def prompt_quit(self):
        self._exit(prompt=True, restart=False)

    @QtCore.Slot()
    def restart(self):
        self._exit(prompt=False, restart=True)

    @QtCore.Slot()
    def prompt_restart(self):
        self._exit(prompt=True, restart=True)

    def interrupt_quit(self):
        if not self._shutting_down:
            self.quit()
            return
        QtCore.QCoreApplication.exit(1)
