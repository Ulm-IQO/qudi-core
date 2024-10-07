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
from functools import partial
from logging import DEBUG, INFO, Logger
from PySide2 import QtCore, QtWidgets, QtGui
from typing import Optional, Union, List, Sequence

from qudi.core.logger import init_rotating_file_handler, init_record_model_handler, clear_handlers
from qudi.core.logger import get_logger, set_log_level
from qudi.util.paths import get_default_log_dir, set_default_data_dir
from qudi.util.mutex import Mutex
from qudi.util.colordefs import QudiMatplotlibStyle
from qudi.core.config import Configuration, ValidationError, YAMLError
from qudi.core.watchdog import AppWatchdog
from qudi.core.module import ModuleState, ModuleBase
from qudi.core.modulemanager import ModuleManager
from qudi.core.threadmanager import ThreadManager
from qudi.core.gui import configure_pyqtgraph, initialize_app_icon, set_theme, set_stylesheet
from qudi.core.gui import close_windows
from qudi.core.servers import RemoteModulesServer, QudiNamespaceServer
from qudi.core.trayicon import QudiTrayIcon
from qudi.core.message import prompt_restart, prompt_shutdown


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
    tray_icon: Union[QudiTrayIcon, None]
    _configured_extension_paths: List[str]
    _is_running: bool
    _shutting_down: bool

    @staticmethod
    def _remove_extensions_from_path(extensions: Sequence[str]) -> None:
        """ Clean up previously configured expansion paths from sys.path """
        for ext_path in extensions:
            try:
                sys.path.remove(ext_path)
            except ValueError:
                pass

    @staticmethod
    def _add_extensions_to_path(extensions: Sequence[str]) -> List[str]:
        """ Add extension paths to beginning of sys.path if not already present """
        insert_index = 1
        added_extensions = list()
        for ext_path in reversed(extensions):
            if ext_path not in sys.path:
                sys.path.insert(insert_index, ext_path)
                added_extensions.append(ext_path)
        return added_extensions

    @classmethod
    def instance(cls):
        if cls._instance is None:
            return None
        return cls._instance()

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

        # Setup environment variables
        setup_environment()

        # Load configuration from disc if possible
        self.configuration = Configuration()
        try:
            self.configuration.load(config_file, set_default=True)
        except ValueError:
            self.log.info('No qudi configuration file specified. Using empty default config.')
        except (ValidationError, YAMLError):
            self.log.exception('Invalid qudi configuration file specified. '
                               'Falling back to default config.')
        if self.configuration.file_path is None:
            print('> Default configuration loaded')
            self.log.info('Default configuration loaded')
        else:
            print(f'> Configuration loaded from "{self.configuration.file_path}"...')
            self.log.info(f'Configuration loaded from "{self.configuration.file_path}"...')

        # Add extensions to PATH
        if self.configuration['extension_paths']:
            self._configured_extension_paths = self._add_extensions_to_path(
                self.configuration['extension_paths']
            )

        # Set default data directory globally
        set_default_data_dir(root=self.configuration['default_data_dir'],
                             use_daily_dirs=self.configuration['daily_data_dirs'])

        # initialize thread manager and module manager
        self.thread_manager = ThreadManager(parent=self)
        self.module_manager = ModuleManager(config=self.configuration, parent=self)

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

        self._is_running = False
        self._shutting_down = False

        print('> Qudi configuration complete!')
        self.log.info('Qudi configuration complete!')

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

    @property
    def is_running(self) -> bool:
        return self._is_running

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
        if self.module_manager.has_main_gui:
            self.tray_icon = QudiTrayIcon(quit_callback=self.quit,
                                          restart_callback=self.restart,
                                          main_gui_callback=self.module_manager.activate_main_gui)
        else:
            self.tray_icon = QudiTrayIcon(quit_callback=self.quit,
                                          restart_callback=self.restart)
        for name in self.module_manager.module_names:
            if self.module_manager.module_base(name) == ModuleBase.GUI:
                self.tray_icon.add_module_action(
                    name=name,
                    callback=partial(self.module_manager.activate_module, name)
                )
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
                for name in self.module_manager.module_names:
                    if self.module_manager.module_state(name) == ModuleState.LOCKED:
                        locked_modules = True
                        break

                # Prompt user either via GUI or command line
                if not self.no_gui and self.module_manager.has_main_gui:
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
            self.module_manager.deactivate_all_modules()
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
