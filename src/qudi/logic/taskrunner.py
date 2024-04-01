# -*- coding: utf-8 -*-
"""
This file contains the Qudi task runner module.

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

from PySide2 import QtCore
from typing import Any, Dict, Union, Tuple, Optional

from qudi.util.mutex import Mutex
from qudi.core.module import LogicBase
from qudi.core.task import ModuleTaskManager, ModuleTaskState
from qudi.core.configoption import ConfigOption


# Detect if this module has been reloaded
_reloaded: bool
try:
    _reloaded
except NameError:
    _reloaded = False  # means the module is being imported
else:
    _reloaded = True  # means the module is being reloaded


class TaskRunnerLogic(LogicBase):
    """ Lightweight wrapper logic for qudi.core.task.ModuleTaskManager control """

    _task_manager: Union[ModuleTaskManager, None]

    _module_task_configs = ConfigOption(name='module_tasks', default=dict(), missing='warn')

    _sigRunTask = QtCore.Signal(str)  # task name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = Mutex()
        self._task_manager = None

    def on_activate(self) -> None:
        """ Initialise task runner """
        self._task_manager = ModuleTaskManager(tasks_configuration=self._module_task_configs,
                                               module_manager=self._qudi_main.module_manager,
                                               thread_manager=self._qudi_main.thread_manager,
                                               reload=_reloaded,
                                               parent=self)
        self._sigRunTask.connect(self._task_manager.run, QtCore.Qt.QueuedConnection)

    def on_deactivate(self) -> None:
        """ Shut down task runner """
        self._sigRunTask.disconnect()
        try:
            self._task_manager.terminate()
        except AttributeError:
            pass
        finally:
            self._task_manager = None

    @property
    def data_model(self) -> ModuleTaskManager:
        return self._task_manager

    def task_state(self, name: str) -> ModuleTaskState:
        return self._task_manager.get_state(name)

    def task_result(self, name: str) -> Tuple[Any, bool]:
        return self._task_manager.get_result(name)

    def task_arguments(self, name: str) -> Dict[str, Any]:
        return self._task_manager.get_arguments(name)

    def run_task(self, name: str, /, **kwargs) -> None:
        with self._lock:
            self._task_manager.set_arguments(name, **kwargs)
            self._sigRunTask.emit(name)

    def interrupt_task(self, name: str) -> None:
        self._task_manager.interrupt(name)
