# -*- coding: utf-8 -*-

"""
This file contains unit tests for all qudi fit routines for exponential decay models.

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

from qudi.core import application
import numpy as np
import sys
import os
import pytest
from PySide2 import QtCore, QtWidgets
from PySide2.QtCore import QTimer


SEED = 42
rng = np.random.default_rng(SEED)
NUM_TESTS = 10
DEFAULT_LOGFILE = 'qudi.log'
RUN_SUCCESS_STR = 'Starting Qt event loop'

@pytest.fixture(scope="session")
def qudi_instance():
    return application.Qudi()
    
@pytest.fixture(scope="session")
def log_file(qudi_instance):
    return os.path.join(qudi_instance.log_dir, DEFAULT_LOGFILE)

@pytest.fixture(scope="session")
def qt_app():
    return QtWidgets.QApplication()


def test_qudi_excepthook_handled(qudi_instance,log_file):
    """ Test for handled exceptions that will be logged """
    try:
        1 / 0
    except Exception as ex:
        qudi_instance._qudi_excepthook(ex.__class__, ex, ex.__traceback__)

        logs = open(log_file).readlines()
        f_line = logs[0]
        current_file = os.path.basename(__file__).split('.')[0]
        assert current_file in f_line
        l_line = logs[-1]
        assert ex.__class__.__name__ in l_line


def test_qudi_excepthook_unhandled(qudi_instance,log_file):
    """ Test for unhandled exceptions which won't be logged """
    try:
        sys.exit()
    except SystemExit as ex:
        qudi_instance._qudi_excepthook(ex.__class__, ex, ex.__traceback__)

        logs = open(log_file).readlines()
        l_line = logs[-1]
        assert ex.__class__.__name__ not in l_line
        
def test_configure_qudi(qudi_instance,qt_app):
    """ Test whether modules are loaded upon configuring qudi instance"""
    assert not bool(qudi_instance.module_manager.modules)
            
    qudi_instance._configure_qudi()
    
    #print(len(qudi_instance.module_manager.modules)) # 43 modules 
    assert bool(qudi_instance.module_manager.modules)


def test_run_exit(qudi_instance,qt_app,log_file):
    try:
        QTimer.singleShot(5000, qt_app.quit)
        qudi_instance.run()
    except SystemExit as e:
        logs = '\n'.join(open(log_file).readlines())
        assert RUN_SUCCESS_STR in logs
        assert not qudi_instance.is_running