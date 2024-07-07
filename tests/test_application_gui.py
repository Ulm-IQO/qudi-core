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

from qudi.core import modulemanager
from qudi.core.logger import get_logger
import numpy as np
import sys
import os
from PySide2.QtCore import QTimer
LOGGER = get_logger(__name__)



RUN_SUCCESS_STR = 'Starting Qt event loop'
CONFIG = 'C:/qudi/qudi-core/tests/dummy.cfg'
CONFIG = 'C:/qudi/default.cfg'


def test_qudi_excepthook_handled(qudi_instance,caplog):
    """Test for handled exceptions that will be logged
    Parameters
    ----------
    qudi_instance : fixture
        fixture for Qudi instance
    caplog : fixture
        pytest fixture to capture logs
    """
    try:
        1 / 0
    except Exception as ex:
        qudi_instance._qudi_excepthook(ex.__class__, ex, ex.__traceback__)
        current_file = os.path.basename(__file__).split('.')[0]
        assert current_file in caplog.text
        assert ex.__class__.__name__ in caplog.text


def test_qudi_excepthook_unhandled(qudi_instance,caplog):
    """Test for unhandled exceptions which won't be logged
    Parameters
    ----------
    qudi_instance : fixture
        fixture for Qudi instance
    caplog : fixture
        pytest fixture to capture logs
    """    
    try:
        sys.exit()
    except SystemExit as ex:
        qudi_instance._qudi_excepthook(ex.__class__, ex, ex.__traceback__)
        assert ex.__class__.__name__ not in caplog.text
        
def test_configure_qudi(qudi_instance,qt_app,config):
    """Test whether modules are loaded upon configuring qudi instance
    Parameters
    ----------
    qudi_instance : fixture
        fixture for Qudi instance
    qt_app : fixture
        fixture for QT app
    config : fixture
        fixture for loaded yaml config
    """    
    assert not bool(qudi_instance.module_manager.modules)
            
    qudi_instance._configure_qudi()

    for base in ['logic', 'gui', 'hardware']:
        for module_name, _ in config[base].items():
            assert module_name in qudi_instance.module_manager.module_names
            assert isinstance(qudi_instance.module_manager.modules[module_name], modulemanager.ManagedModule)

    
    #print(len(qudi_instance.module_manager.modules)) # 43 modules 


def test_run_exit(qudi_instance,qt_app,caplog, teardown_modules):
    """Test if the qudi application runs and exits properly
    Parameters
    ----------
    qudi_instance : fixture
        fixture for Qudi instance
    qt_app : fixture
        fixture for QT app
    caplog : fixture
        pytest fixture to capture logs
    """    
    try:
        QTimer.singleShot(5000, qt_app.quit)
        qudi_instance.run()
    except SystemExit as e:
        assert RUN_SUCCESS_STR in caplog.text
        assert not qudi_instance.is_running 




