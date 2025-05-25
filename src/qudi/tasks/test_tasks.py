# -*- coding: utf-8 -*-

"""
This file contains tasks for testing the qudi ModuleTask functionality.

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

import time
from typing import Iterable, Sequence, Mapping, Optional, Tuple

from qudi.core.task import ModuleTask, ModuleTaskState
from qudi.core.connector import Connector
from qudi.logic.taskrunner import TaskRunnerLogic


ACTIVATION_TIME: float = 3.0
DEACTIVATION_TIME: float = 3.0


class TestTask(ModuleTask):

    # _derp = Connector(name='derp', interface='TemplateLogic')

    def _activate(self) -> None:
        start = time.time()
        while (time.time() - start) < ACTIVATION_TIME:
            time.sleep(ACTIVATION_TIME / 3)
            self._check_interrupt()

    def _deactivate(self) -> None:
        time.sleep(DEACTIVATION_TIME)

    def _run(self, str_arg: str, int_arg: int, duration_sec: Optional[float] = 5):
        start = time.time()
        while (time.time() - start) < duration_sec:
            time.sleep(duration_sec / 3)
            self._check_interrupt()
        return str_arg, int_arg


class TestTask2(ModuleTask):

    _derp = Connector(name='derp', interface=TaskRunnerLogic)

    def _activate(self) -> None:
        start = time.time()
        while (time.time() - start) < ACTIVATION_TIME:
            time.sleep(ACTIVATION_TIME / 3)
            self._check_interrupt()

    def _deactivate(self) -> None:
        time.sleep(DEACTIVATION_TIME)

    def _run(self,
             seq_arg: Sequence[int],
             iter_arg: Iterable[str],
             map_arg: Mapping[str, int],
             opt_arg: Optional[int] = 42,
             duration_sec: Optional[float] = 5
             ) -> Tuple[Sequence[int], Iterable[str], Mapping[str, int], int]:
        assert self._derp.task_state(self.nametag) == ModuleTaskState.RUNNING
        start = time.time()
        while (time.time() - start) < duration_sec:
            time.sleep(duration_sec / 3)
            self._check_interrupt()
        return seq_arg, iter_arg, map_arg, opt_arg
