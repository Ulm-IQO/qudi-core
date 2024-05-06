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

from PySide2 import QtCore

from qudi.core.module import LogicBase
from qudi.core.connector import Connector


class ProblemLogic(LogicBase):
    exceptionlogic = Connector(interface="ExceptionLogic")
    signal = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_activate(self):
        self.connect_signal()
        self.log.debug("Finished activation")

    def on_deactivate(self):
        self.log.debug("Deactivating Exception Logic.")

    def connect_signal(self, connection: int = 1):
        if connection == 1:
            self.signal.connect(
                self.exceptionlogic().exception_method, QtCore.Qt.QueuedConnection
            )
        elif connection == 2:
            self.signal.connect(
                self.exceptionlogic().try_except_method, QtCore.Qt.QueuedConnection
            )
        elif connection == 3:
            self.signal.connect(self.test_exception_method, QtCore.Qt.QueuedConnection)
        elif connection == 4:
            self.signal.connect(
                self.test_try_except_exception_method, QtCore.Qt.QueuedConnection
            )

    def emit_signal(self):
        self.log.debug("Emitting signal.")
        self.signal.emit()

    def test_exception_method(self):
        self.log.debug("Testing exception_method.")
        self.exceptionlogic().exception_method()
        # As expected the function throws an exception
        # and the code below can't be reached
        self.log.error("Code after exception throw is never reached.")

    def test_try_except_exception_method(self):
        try:
            self.log.debug(
                "Testing exception_method by wrapping in try,except statement."
            )
            self.exceptionlogic().exception_method()
            # As expected the function throws an exception
            # which is caught by the try, except statement
            # thus the code below can be reached
        except Exception as e:
            self.log.error(e)
            self.log.debug(
                "Code after exception throw is reached and exception is logged."
            )
            raise Exception from e
