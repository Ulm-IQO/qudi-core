# -*- coding: utf-8 -*-

"""
This file contains scripts for testing the qudi.core.scripting package.

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

from typing import Iterable, Sequence, Mapping, Union, Any, Optional, Tuple

from qudi.core.scripting.moduletask import ModuleTask
from qudi.core.connector import Connector


class TestTask(ModuleTask):

    _derp = Connector(name='derp', interface='TemplateLogic')

    def _setup(self) -> None:
        i = 0
        for i in range(100000000):
            i += 1

    def _cleanup(self) -> None:
        i = 0
        for i in range(100000000):
            i += 1

    def _run(self, pos_arg='abc', kw_arg=42):
        i = 0
        for i in range(10000000):
            self._check_interrupt()
            i += 1


class TestTask2(ModuleTask):

    _derp = Connector(name='derp', interface='TemplateLogic')

    def _setup(self) -> None:
        i = 0
        for i in range(100000000):
            i += 1

    def _cleanup(self) -> None:
        i = 0
        for i in range(100000000):
            i += 1

    def _run(self, seq_arg: Sequence[int], iter_arg: Iterable[str], map_arg: Mapping[str, int],
             opt_arg: Optional[int] = 42
             ) -> Tuple[Sequence[int], Iterable[str], Mapping[str, int], int]:
        i = 0
        for i in range(10000000):
            if i % 100 == 0:
                self._check_interrupt()
            i += 1
        return seq_arg, iter_arg, map_arg, opt_arg
