# -*- coding: utf-8 -*-

"""
This file contains a task class to run with qudi module dependencies as well as various
helper classes to run and manage these tasks.

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

__all__ = ['ModuleTask', 'ModuleTaskState', 'ModuleTaskStateError', 'ModuleTaskInterrupted',
           'ModuleTaskManager', 'ModuleTaskWorker', 'import_module_task']

import inspect
import importlib
from enum import Enum
from abc import abstractmethod
from PySide2 import QtCore
from typing import Mapping, Any, Optional, MutableMapping, Union, Tuple, Dict, List, Callable, Type
from typing import final

from qudi.util.mutex import Mutex
from qudi.util.helpers import call_slot_from_native_thread
from qudi.core.object import QudiObject
from qudi.core.module import Base
from qudi.core.modulemanager import ModuleManager
from qudi.core.threadmanager import ThreadManager


class ModuleTaskStateError(RuntimeError):
    """ Custom exception class to indicate a failed or invalid ModuleTask state change """
    pass


class ModuleTaskInterrupted(Exception):
    """ Custom exception class to indicate that a ModuleTask execution has been interrupted """
    pass


class ModuleTaskState(Enum):
    """ Qudi ModuleTask state enum with name strings as values and convenient state checking
    properties
    """
    IDLE = 'idle'
    RUNNING = 'running'

    @property
    def idle(self) -> bool:
        return self is self.IDLE

    @property
    def running(self) -> bool:
        return self is self.RUNNING


class ModuleTask(QudiObject):
    """ Abstract base class for a runnable qudi task.
    Subclasses MUST implement the main "_run" method with a desired method signature that can
    return a result.
    Subclasses CAN implement "_activate"/"_deactivate" method to optionally setup/cleanup
    tasks before/after running. These methods must take no arguments and return none.

    Implementations of "_activate" and "_run" methods can occasionally call "_check_interrupt" to
    raise "ModuleTaskInterrupted" at that point if an interrupt is requested. In that case the task
    will immediately jump to call "_deactivate" (if implemented) so checking should happen at
    points where "_deactivate" can properly clean up afterward. This also happens if any exception
    is encountered in "_activate" or "_run".

    TL;DR
    Minimal implementations must simply provide a "_run" method.
    """

    interrupted: bool

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

        Override in subclass if you want anything else than this default implementation.
        Make sure custom implementations of this property are compatible with _run!
        """
        return inspect.signature(cls._run).return_annotation

    def __init__(self,
                 options: Optional[Mapping[str, Any]] = None,
                 connections: Optional[MutableMapping[str, Any]] = None,
                 nametag: Optional[str] = '',
                 parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(options, connections, nametag, parent=parent)
        self.interrupted = False

    @final
    def interrupt(self) -> None:
        self.interrupted = True

    @final
    def _check_interrupt(self) -> None:
        """ Implementations of "_run" should occasionally call this method in order to break
        execution early if another thread has interrupted this script in the meantime.
        """
        if self.interrupted:
            raise ModuleTaskInterrupted

    @final
    def __call__(self, **kwargs) -> Any:
        """ Run this task like a function. See concrete "_run" implementation for method signature.
        Will block until task is complete.

        DO NOT OVERRIDE IN SUBCLASS!
        """
        self.log.info(f'Starting task: "{self.nametag}"')
        try:
            try:
                self._activate()
                result = self._run(**kwargs)
            finally:
                self._deactivate()
        except ModuleTaskInterrupted:
            self.log.info(f'Task interrupted: "{self.nametag}"')
            raise
        except Exception as err:
            raise ModuleTaskStateError(f'Exception running task: "{self.nametag}"') from err
        self.log.info(f'Task finished successfully: "{self.nametag}"')
        return result

    # Implement "_activate" and "_deactivate" in subclass if needed. They will simply do nothing
    # by default.
    # You MUST in any case implement "_run" in a subclass (see: ModuleTask._run).
    @abstractmethod
    def _run(self, **kwargs) -> Any:
        """ The actual script to be run. Must be implemented in a subclass. Keyword arguments only.
        """
        raise NotImplementedError(
            f'No "_run" main method implemented for "{self.__module__}.{self.__class__.__name__}"'
        )

    def _activate(self) -> None:
        """ Optional setup procedure to be performed before "_run" is called.
        Raising an exception in here will cause the task to directly call "_deactivate" and skip the
        "_run" call. The same is true for calls to "_check_interrupt" if an interrupt has been
        requested beforehand.

        Implement in subclass.
        """
        self._check_interrupt()

    def _deactivate(self) -> None:
        """ Optional cleanup procedure to be performed after "_run" has been called. This method is
        always called, even if "_activate" or "_run" raise an exception.

        Implement in subclass.
        """
        pass


class ModuleTaskWorker(QtCore.QObject):
    """ Worker QObject to spawn, configure and run ModuleTask instances and signal current
    ModuleTaskState.

    Can be considered thread-safe.
    """

    _arguments: Dict[str, Any]
    _result: Tuple[Any, bool]
    _name: str
    _task_type: Type[ModuleTask]
    _options: Dict[str, Any]
    _connect: Dict[str, str]
    _current_state: ModuleTaskState
    __task: Union[None, ModuleTask]

    sigStateChanged = QtCore.Signal(ModuleTaskState)
    sigArgumentsChanged = QtCore.Signal(dict)

    def __init__(self,
                 name: str,
                 task_type: Type[ModuleTask],
                 module_manager: ModuleManager,
                 options: Optional[Mapping[str, Any]] = None,
                 connect: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__()
        # ModuleTaskWorker QObjects must not have a parent in order to be used as threaded workers
        self._name = name
        self._task_type = task_type
        self._options = dict() if options is None else options
        self._connect = dict() if connect is None else connect
        self._module_manager = module_manager

        self._lock = Mutex()
        self._arguments = {
            name: param.default for name, param in task_type.call_parameters().items() if
            param.default is not inspect.Parameter.empty
        }
        self._result = (None, False)
        self._current_state = ModuleTaskState.IDLE
        self.__task = None

    @property
    def call_parameters(self) -> Dict[str, inspect.Parameter]:
        return self._task_type.call_parameters()

    @property
    def result_annotation(self) -> Union[Any, inspect.Signature.empty]:
        return self._task_type.result_annotation()

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> ModuleTaskState:
        return self._current_state

    @property
    def arguments(self) -> Dict[str, Any]:
        return self._arguments.copy()

    @property
    def result(self) -> Tuple[Any, bool]:
        return self._result

    def set_arguments(self, **kwargs) -> None:
        self._arguments = kwargs
        self.sigArgumentsChanged.emit(self.arguments)

    @QtCore.Slot()
    def interrupt(self) -> None:
        try:
            self.__task.interrupt()
        except AttributeError:
            pass

    @QtCore.Slot()
    def run(self) -> None:
        """ """
        with self._lock:
            self._result = (None, False)
            try:
                connections = self.__activate_connected_modules()
                self.__task = self._task_type(options=self._options,
                                              connections=connections,
                                              nametag=self._name,
                                              parent=self)
                self.__update_state(ModuleTaskState.RUNNING)
                self._result = (self.__task(**self._arguments), True)
            except ModuleTaskInterrupted:
                pass
            except ModuleTaskStateError:
                self.__task.log.exception(f'Exception running task: "{self._name}"')
            finally:
                self.__task = None
                self.__update_state(ModuleTaskState.IDLE)

    def __activate_connected_modules(self) -> Dict[str, Base]:
        return {name: self._module_manager.get_module_instance(target) for name, target in
                self._connect.items()}

    def __update_state(self, new: ModuleTaskState) -> None:
        self._current_state = new
        self.sigStateChanged.emit(new)


def import_module_task(module: str, cls: str, reload: Optional[bool] = False) -> Type[ModuleTask]:
    """ Import a ModuleTask class from a given module name and class name """
    mod = importlib.import_module(module)
    if reload:
        mod = importlib.reload(mod)
    try:
        task_cls = getattr(mod, cls)
        if not issubclass(task_cls, ModuleTask):
            raise TypeError(f'"{module}.{cls}" is not a subclass of '
                            f'"{ModuleTask.__module__}.{ModuleTask.__name__}"')
    except Exception as err:
        raise ImportError(f'Unable to import ModuleTask "{module}.{cls}"') from err
    return task_cls


class ModuleTaskManager(QtCore.QAbstractTableModel):
    """ Governing instance to monitor and run ModuleTask objects. Doubles as a Qt table model. """

    _thread_manager: ThreadManager
    _tasks: List[ModuleTaskWorker]
    _name_to_index: Dict[str, int]
    _headers: Tuple[str, str, str] = ('Arguments', 'State', 'Result')

    def __init__(self,
                 tasks_configuration: Mapping[str, Mapping[str, Any]],
                 module_manager: ModuleManager,
                 thread_manager: ThreadManager,
                 reload: Optional[bool] = False,
                 parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        self._thread_manager = thread_manager
        self._tasks = list()
        self._name_to_index = dict()
        for name, config in tasks_configuration.items():
            self.__add_worker(module_manager, name, config, reload)

    def terminate(self) -> None:
        """ """
        self.beginResetModel()
        for name in list(reversed(self._name_to_index)):
            self.__remove_worker(name)
        self.endResetModel()

    def rowCount(self, parent: Optional[QtCore.QModelIndex] = None) -> int:
        return len(self._tasks)

    def columnCount(self, parent: Optional[QtCore.QModelIndex] = None) -> int:
        return len(self._headers)

    def data(self,
             index: QtCore.QModelIndex,
             role: Optional[QtCore.Qt.ItemDataRole] = QtCore.Qt.DisplayRole) -> Any:
        try:
            task = self._tasks[index.row()]
        except IndexError:
            return None
        if role == QtCore.Qt.DisplayRole:
            col = index.column()
            if col == 0:
                return task.arguments
            elif col == 1:
                return task.state
            elif col == 2:
                return task.result
        elif role == QtCore.Qt.UserRole:
            return task
        return None

    def setData(self,
                index: QtCore.QModelIndex,
                value: Any,
                role: Optional[QtCore.Qt.ItemDataRole] = QtCore.Qt.EditRole) -> bool:
        if (role == QtCore.Qt.EditRole) and (index.column() == 0):
            try:
                task = self._tasks[index.row()]
            except IndexError:
                pass
            else:
                try:
                    task.set_arguments(**value)
                except TypeError:
                    pass
                else:
                    return True
        return False

    def headerData(self,
                   section: int,
                   orientation: QtCore.Qt.Orientation,
                   role: Optional[QtCore.Qt.ItemDataRole] = QtCore.Qt.DisplayRole
                   ) -> Union[str, None]:
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                try:
                    return self._headers[section]
                except IndexError:
                    pass
            elif role == QtCore.Qt.UserRole:
                return 'ModuleTaskWorker'
        else:
            if role == QtCore.Qt.DisplayRole:
                try:
                    return self._tasks[section].name
                except IndexError:
                    pass
        return None

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        flags = QtCore.Qt.ItemIsEnabled
        if 0 <= index.column() <= 1:
            flags |= QtCore.Qt.ItemIsEditable
        return flags

    def get_call_parameters(self, name: str) -> Dict[str, inspect.Parameter]:
        task, _ = self._get_task(name)
        return task.call_parameters

    def get_result_annotation(self, name: str) -> Union[Any, inspect.Signature.empty]:
        task, _ = self._get_task(name)
        return task.result_annotation

    def set_arguments(self, name: str, /, **kwargs) -> None:
        """ Set keyword arguments of named task """
        task, _ = self._get_task(name)
        task.set_arguments(**kwargs)

    def get_arguments(self, name: str) -> Dict[str, Any]:
        task, _ = self._get_task(name)
        return task.arguments

    def get_result(self, name: str) -> Tuple[Any, bool]:
        task, _ = self._get_task(name)
        return task.result

    def get_state(self, name: str) -> ModuleTaskState:
        task, _ = self._get_task(name)
        return task.state

    def interrupt(self, name: str) -> None:
        """ Interrupt a task by name """
        task, _ = self._get_task(name)
        task.interrupt()

    def run(self, name: str) -> None:
        """ Run a task by name in its own thread.
        Returns immediately and does not block until task has finished (or failed).
        """
        task, _ = self._get_task(name)
        call_slot_from_native_thread(task, 'run', blocking=False)

    def _get_task(self, name: str) -> Tuple[ModuleTaskWorker, int]:
        try:
            row = self._name_to_index[name]
        except KeyError:
            raise ValueError(f'No task found by name "{name}"') from None
        return self._tasks[row], row

    def __add_worker(self,
                     module_manager: ModuleManager,
                     name: str,
                     config: Mapping[str, Any],
                     reload: Optional[bool] = False) -> None:
        if len(name) < 1:
            raise ValueError('Task name must be non-empty string')
        if name in self._name_to_index:
            raise ValueError(f'Task with name "{name}" already registered')
        module, cls = config['module.Class'].rsplit('.', 1)
        task_type = import_module_task(module=module, cls=cls, reload=reload)
        worker = ModuleTaskWorker(name=name,
                                  task_type=task_type,
                                  module_manager=module_manager,
                                  options=config.get('options', None),
                                  connect=config.get('connect', None))
        thread = self._thread_manager.get_new_thread(f'task-{name}')
        worker.moveToThread(thread)
        index = len(self._tasks)
        worker.sigStateChanged.connect(self.__get_state_updated_callback(index),
                                       QtCore.Qt.QueuedConnection)
        worker.sigArgumentsChanged.connect(self.__get_arguments_updated_callback(index),
                                           QtCore.Qt.QueuedConnection)
        thread.start()
        self._tasks.append(worker)
        self._name_to_index[name] = index

    def __remove_worker(self, name: str) -> None:
        try:
            index = self._name_to_index.pop(name)
        except KeyError:
            return
        task = self._tasks.pop(index)
        task.sigStateChanged.disconnect()
        task.sigArgumentsChanged.disconnect()
        task.interrupt()
        thread_name = f'task-{name}'
        self._thread_manager.quit_thread(thread_name)
        self._thread_manager.join_thread(thread_name)

    def __get_arguments_updated_callback(self, row: int) -> Callable[[], None]:

        def updated_callback():
            index = self.index(row, 0)
            self.dataChanged.emit(index, index)

        return updated_callback

    def __get_state_updated_callback(self, row: int) -> Callable[[], None]:

        def updated_callback():
            self.dataChanged.emit(self.index(row, 1), self.index(row, 2))

        return updated_callback
