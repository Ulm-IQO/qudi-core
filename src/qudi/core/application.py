# -*- coding: utf-8 -*-
"""
This file contains the qudi Manager class.

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

import gc
import sys
import os
import weakref
import inspect
import traceback
import faulthandler
from logging import DEBUG, INFO
from PySide2 import QtCore, QtWidgets

from qudi.core.logger import init_rotating_file_handler, init_record_model_handler, clear_handlers
from qudi.core.logger import get_logger, set_log_level
from qudi.util.paths import get_main_dir, get_default_log_dir
from qudi.util.mutex import Mutex
from qudi.util.colordefs import QudiMatplotlibStyle
from qudi.core.config import Configuration, ValidationError, YAMLError
from qudi.core.watchdog import AppWatchdog
from qudi.core.modulemanager import ModuleManager
from qudi.core.threadmanager import ThreadManager
from qudi.core.gui.gui import Gui
from qudi.core.servers import RemoteModulesServer, QudiNamespaceServer

# Use non-GUI "Agg" backend for matplotlib by default since it is reasonably thread-safe. Otherwise
# you can only plot from main thread and not e.g. in a logic module.
# This causes qudi to not be able to spawn matplotlib GUIs (by calling matplotlib.pyplot.show())
try:
    import matplotlib as _mpl
    _mpl.use('Agg')
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

# Make icons work on non-X11 platforms, import a custom theme
if sys.platform == 'win32':
    try:
        import ctypes
        myappid = 'qudicore-app'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except ImportError:
        raise
    except:
        print('SetCurrentProcessExplicitAppUserModelID failed! This is probably not Microsoft '
              'Windows!')

# Set default Qt locale to "C" in order to avoid surprises with number formats and other things
# QtCore.QLocale.setDefault(QtCore.QLocale('en_US'))
QtCore.QLocale.setDefault(QtCore.QLocale.c())


class Qudi(QtCore.QObject):
    """

    """
    _instance = None
    _run_lock = Mutex()
    _quit_lock = Mutex()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None or cls._instance() is None:
            obj = super().__new__(cls, *args, **kwargs)
            cls._instance = weakref.ref(obj)
            return obj
        raise RuntimeError(
            'Only one qudi instance per process possible (Singleton). Please use '
            'Qudi.instance() to get a reference to the already created instance.'
        )

    def __init__(self, no_gui=False, debug=False, log_dir='', config_file=None):
        super().__init__()

        # CLI arguments
        self.no_gui = bool(no_gui)
        self.debug_mode = bool(debug)
        self.log_dir = str(log_dir) if os.path.isdir(log_dir) else get_default_log_dir(
            create_missing=True)

        # Disable pyqtgraph "application exit workarounds" because they cause errors on exit
        try:
            import pyqtgraph
            pyqtgraph.setConfigOption('exitCleanup', False)
        except ImportError:
            pass

        # Enable stack trace output for SIGSEGV, SIGFPE, SIGABRT, SIGBUS and SIGILL signals
        # -> e.g. for segmentation faults
        faulthandler.disable()
        faulthandler.enable(all_threads=True)

        # install logging facility and set logging level
        init_record_model_handler(max_records=10000)
        init_rotating_file_handler(path=self.log_dir)
        set_log_level(DEBUG if self.debug_mode else INFO)

        # Set up logger for qudi main instance
        self.log = get_logger(__class__.__name__)  # will be "qudi.Qudi" in custom logger
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
                qudi=self,
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
        self.gui = None

        self._configured_extension_paths = list()
        self._is_running = False
        self._shutting_down = False

        # Set qudi style for matplotlib
        try:
            import matplotlib.pyplot as plt
            plt.style.use(QudiMatplotlibStyle.style)
        except ImportError:
            pass

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
    def is_running(self):
        return self._is_running

    def _remove_extensions_from_path(self):
        # Clean up previously configured expansion paths
        for ext_path in self._configured_extension_paths:
            try:
                sys.path.remove(ext_path)
            except ValueError:
                pass

    def _add_extensions_to_path(self):
        extensions = self.configuration['extension_paths']
        # Add qudi extension paths to sys.path
        insert_index = 1
        for ext_path in reversed(extensions):
            sys.path.insert(insert_index, ext_path)
        self._configured_extension_paths = extensions

    @QtCore.Slot()
    def _configure_qudi(self):
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
        for base in ['hardware', 'logic', 'gui']:
            # Create ManagedModule instance by adding each module to ModuleManager
            for module_name, module_cfg in self.configuration[base].items():
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

    def _start_gui(self):
        if self.no_gui:
            return
        self.gui = Gui(qudi_instance=self, stylesheet_path=self.configuration['stylesheet'])
        if not self.configuration['hide_manager_window']:
            self.gui.activate_main_gui()

    def _start_startup_modules(self):
        for module in self.configuration['startup_modules']:
            print(f'> Loading startup module: {module}')
            self.log.info(f'Loading startup module: {module}')
            # Do not crash if a module can not be started
            try:
                self.module_manager.activate_module(module)
            except:
                self.log.exception(f'Unable to activate autostart module "{module}":')

    def run(self):
        """
        """
        with self._run_lock:
            if self._is_running:
                raise RuntimeError('Qudi is already running!')

            # Notify startup
            startup_info = f'Starting qudi{" in debug mode..." if self.debug_mode else "..."}'
            self.log.info(startup_info)
            print(f'> {startup_info}')

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

            # Apply configuration to qudi
            self._configure_qudi()

            # Start GUI if needed
            self._start_gui()

            # Start the startup modules defined in the config file
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
                broken_modules = False
                for module in self.module_manager.values():
                    if module.is_busy:
                        locked_modules = True
                    elif module.state == 'BROKEN':
                        broken_modules = True
                    if broken_modules and locked_modules:
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
                    if restart:
                        if not self.gui.prompt_restart(locked_modules):
                            self._shutting_down = False
                            return
                    else:
                        if not self.gui.prompt_shutdown(locked_modules):
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
            self.module_manager.stop_all_modules()
            self.module_manager.clear()
            QtCore.QCoreApplication.instance().processEvents()
            if not self.no_gui:
                self.log.info('Closing main GUI...')
                print('> Closing main GUI...')
                self.gui.deactivate_main_gui()
                self.log.info('Closing remaining windows...')
                print('> Closing remaining windows...')
                self.gui.close_windows()
                self.gui.close_system_tray_icon()
                QtCore.QCoreApplication.instance().processEvents()
            self.log.info('Stopping remaining threads...')
            print('> Stopping remaining threads...')
            self.thread_manager.quit_all_threads()
            QtCore.QCoreApplication.instance().processEvents()
            clear_handlers()
            gc.collect()  # Explicit gc call to prevent Qt C++ extensions from using deleted Python objects
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
