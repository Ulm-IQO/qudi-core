# -*- coding: utf-8 -*-

"""
This file contains a basic script class to run with qudi module dependencies as well as various
helper classes to run and manage these scripts.

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

__all__ = ['import_module_script', 'ModuleScript', 'ModuleScriptsDictTableModel',
           'ModuleScriptInterrupted']

import importlib
import copy
import inspect
from abc import abstractmethod
from PySide2 import QtCore
from logging import Logger
from typing import Mapping, Any, Type, Optional, Union, Dict, MutableMapping

from qudi.core.meta import QudiObject
from qudi.core.module import Base
from qudi.core.connector import ModuleConnectionError
from qudi.core.logger import get_logger
from qudi.util.models import DictTableModel
from qudi.util.mutex import Mutex


class ModuleScriptInterrupted(Exception):
    """ Custom exception class to indicate that a ModuleScript execution has been interrupted.
    """
    pass


class ModuleScript(QudiObject):
    """
    The only part that can be interrupted is the _run() method.
    The implementations must occasionally call _check_interrupt() to raise an exception at that
    point if an interrupt is requested.
    """
    # Declare all module connectors used in this script here

    sigFinished = QtCore.Signal()

    def __init__(self):
        # ModuleScript QObjects must not have a parent in order to be used as threaded workers
        super().__init__()

        self._thread_lock = Mutex()
        self.__logger = get_logger(f'{self.__module__}.{self.__class__.__name__}')

        # script arguments and result cache
        self.args = tuple()
        self.kwargs = dict()
        self.result = None

        # Status flags
        self._interrupted = True
        self._success = False
        self._running = False

    @property
    def interrupted(self):
        with self._thread_lock:
            return self._interrupted

    @property
    def log(self) -> Logger:
        return self.__logger

    @property
    def running(self) -> bool:
        with self._thread_lock:
            return self._running

    @property
    def success(self) -> bool:
        with self._thread_lock:
            return self._success

    @classmethod
    def call_parameters(cls) -> Dict[str, inspect.Parameter]:
        """ Call parameters of the _run method implementation.

        Override in subclass if you want anything else than this default implementation.
        Make sure custom implementations of this property are compatible with _run!
        """
        parameters = dict(inspect.signature(cls._run).parameters)
        # Remove first parameter if it is a bound instance method
        if not isinstance(inspect.getattr_static(cls, '_run'), (classmethod, staticmethod)):
            try:
                del parameters[next(iter(parameters))]
            except StopIteration:
                pass
        return parameters

    @classmethod
    def result_annotation(cls) -> Union[Any, inspect.Signature.empty]:
        """ Return type annotation for the _run method implementation.
        Will return inspect.Signature.empty if _run return value is not annotated.
        """
        return inspect.signature(cls._run).return_annotation

    def interrupt(self):
        with self._thread_lock:
            self._interrupted = True

    def __call__(self, *args, **kwargs) -> Any:
        """ Convenience magic method to run this script like a function
        DO NOT OVERRIDE IN SUBCLASS!

        Arguments are passed directly to _run() method.

        @return object: Result of the script method
        """
        self.args = args
        self.kwargs = kwargs
        self.run()
        return self.result

    @QtCore.Slot()
    def run(self) -> None:
        """ Check run prerequisites and execute _run method with pre-cached arguments.
        DO NOT OVERRIDE IN SUBCLASS!
        """
        self.result = None
        with self._thread_lock:
            self._interrupted = False
            self._success = False
            self._running = True
        self.log.debug(f'Running main method with\n\targs: {self.args}\n\tkwargs: {self.kwargs}.')
        # Emit finished signal even if script execution fails. Check success flag.
        try:
            self.result = self._run(*self.args, **self.kwargs)
            with self._thread_lock:
                self._success = True
        except ModuleScriptInterrupted:
            self.log.info(f'Main run method interrupted')
        except:
            self.log.exception('Exception during main run method:')
            raise
        finally:
            with self._thread_lock:
                self._running = False
                self.sigFinished.emit()

    def connect_modules(self, connections: MutableMapping[str, Base]) -> None:
        """ Connects given modules (values) to their respective Connector (keys). """
        # Iterate through all module connectors and try to connect them to targets
        for connector in self._meta['connectors'].values():
            target = connections.pop(connector.name, None)
            if target is None:
                if not connector.optional:
                    raise ModuleConnectionError(
                        f'Mandatory module connector "{connector.name}" not configured.'
                    )
            else:
                connector.connect(self, target)

        # Warn if too many connections have been configured
        if connections:
            self.log.warning(
                f'Module config contains additional connectors that are ignored. Please remove '
                f'the following connections from the configuration: {list(connections)}'
            )

    def disconnect_modules(self) -> None:
        """ Disconnects all Connector instances for this object.

        DO NOT CALL THIS METHOD UNLESS YOU KNOW WHAT YOU ARE DOING!
        """
        for connector in self._meta['connectors'].values():
            connector.disconnect(self)

    def _check_interrupt(self) -> None:
        """ Implementations of _run should occasionally call this method in order to break
        execution early if another thread has interrupted this script in the meantime.
        """
        if self.interrupted:
            raise ModuleScriptInterrupted

    @abstractmethod
    def _run(self, *args, **kwargs) -> Any:
        """ The actual script to be run. Implement only this method in a subclass.
        """
        raise NotImplementedError(f'No _run() method implemented for "{self.__class__.__name__}".')


def import_module_script(module: str, cls: str,
                         reload: Optional[bool] = True) -> Type[ModuleScript]:
    """ Helper function to import ModuleScript sub-classes by name from a given module.
    Reloads the module to import from by default.
    """
    mod = importlib.import_module(module)
    if reload:
        importlib.reload(mod)
    script = getattr(mod, cls)
    if not issubclass(script, ModuleScript):
        raise TypeError(f'Module script to import must be a subclass of {__name__}.ModuleScript')
    return script


class ModuleScriptsDictTableModel(DictTableModel):
    """ Qt compatible table model holding all configured and available ModuleScript subclasses.
    """
    def __init__(self, scripts_config: Optional[Mapping[str, dict]] = None):
        super().__init__(headers=['Name', 'Class'])
        if scripts_config is None:
            scripts_config = dict()
        for name, config in scripts_config.items():
            self.register_script(name, config)

    def register_script(self, name: str, config: dict) -> None:
        if name in self:
            raise KeyError(f'Multiple module script with name "{name}" configured.')
        module, cls = config['module.Class'].rsplit('.', 1)
        self[name] = import_module_script(module, cls, reload=False)
