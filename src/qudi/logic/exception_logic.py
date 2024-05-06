# -*- coding: utf-8 -*-
"""
Interact with switches.

Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-iqo-modules/>

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

from qudi.core.module import LogicBase


class ExceptionLogic(LogicBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_activate(self):
        self.log.debug("Finished activation")

    def on_deactivate(self):
        self.log.debug("Deactivating Exception Logic.")

    def try_except_method(self):
        # Method that wraps exception method into try, except statement.
        # It logs the error and raises another exception from the base exception.
        try:
            self.exception_method()
        except Exception as e:
            self.log.error(e)
            raise Exception from e

    def exception_method(self):
        # Method that logs the calling of itself and just raises an exception.
        self.log.debug("In exception_method.")
        raise Exception("Exception in exception_method")
