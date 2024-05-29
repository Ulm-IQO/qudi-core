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

from qudi.core import application,modulemanager
from qudi.core.logger import get_logger
import numpy as np
import sys
import os
import pytest
from PySide2 import QtCore, QtWidgets
from PySide2.QtCore import QTimer
import weakref
import yaml
LOGGER = get_logger(__name__)



RUN_SUCCESS_STR = 'Starting Qt event loop'
CONFIG = 'C:/qudi/qudi-core/tests/dummy.cfg'
CONFIG = 'C:/qudi/default.cfg'

@pytest.fixture(scope="session")
def qudi_instance():
    instance = application.Qudi.instance()
    if instance is None:
        instance = application.Qudi(config_file=CONFIG)
    instance_weak = weakref.ref(instance)
    return instance_weak()

@pytest.fixture(scope="module")
def qt_app():
    app_cls = QtWidgets.QApplication
    app = app_cls.instance()
    if app is None:
        app = app_cls()
    return app

@pytest.fixture(scope='module')
def config():
    with open(CONFIG) as stream:
        configuration = (yaml.safe_load(stream))
    return configuration

def test_qudi_excepthook_handled(qudi_instance,caplog):
    """ Test for handled exceptions that will be logged """
    try:
        1 / 0
    except Exception as ex:
        qudi_instance._qudi_excepthook(ex.__class__, ex, ex.__traceback__)
        current_file = os.path.basename(__file__).split('.')[0]
        assert current_file in caplog.text
        assert ex.__class__.__name__ in caplog.text


def test_qudi_excepthook_unhandled(qudi_instance,caplog):
    """ Test for unhandled exceptions which won't be logged """
    try:
        sys.exit()
    except SystemExit as ex:
        qudi_instance._qudi_excepthook(ex.__class__, ex, ex.__traceback__)
        assert ex.__class__.__name__ not in caplog.text
        
def test_configure_qudi(qudi_instance,qt_app,config):
    """ Test whether modules are loaded upon configuring qudi instance"""
    assert not bool(qudi_instance.module_manager.modules)
            
    qudi_instance._configure_qudi()

    for base in ['logic', 'gui', 'hardware']:
        for module_name, _ in config[base].items():
            assert module_name in qudi_instance.module_manager.module_names
            assert isinstance(qudi_instance.module_manager.modules[module_name], modulemanager.ManagedModule)

    
    #print(len(qudi_instance.module_manager.modules)) # 43 modules 


def test_run_exit(qudi_instance,qt_app,caplog):
    try:
        QTimer.singleShot(5000, qt_app.quit)
        qudi_instance.run()
    except SystemExit as e:
        assert RUN_SUCCESS_STR in caplog.text
        assert not qudi_instance.is_running 
 
        qt_app.shutdown()
        del qt_app
        
        app_cls = QtWidgets.QApplication
        app = app_cls.instance()
        assert app is None
        
