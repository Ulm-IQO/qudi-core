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

from qudi.core import modulemanager,application
from qudi.core.logger import get_logger
import numpy as np
import yaml
import pytest
from PySide2 import QtCore, QtWidgets
import weakref


CONFIG = 'C:/qudi/qudi-core/tests/dummy.cfg'
CONFIG = 'C:/qudi/default.cfg'


@pytest.fixture(scope="module")
def qt_app():
    app_cls = QtWidgets.QApplication
    app = app_cls.instance()
    if app is None:
        app = app_cls()
    return app

@pytest.fixture(scope="module")
def qudi_instance(qt_app):
    instance = application.Qudi.instance()
    if instance is None:
        instance = application.Qudi(config_file=CONFIG)
    instance_weak = weakref.ref(instance)
    return instance_weak()


@pytest.fixture(scope='module')
def config():
    with open(CONFIG) as stream:
        configuration = (yaml.safe_load(stream))
    return configuration

@pytest.fixture(scope='module')
def sample_module_gui(config):
    sample_base = 'gui'
    sample_module_name, sample_module_cfg = list(config[sample_base].items())[0]
    return sample_base, sample_module_name, sample_module_cfg

@pytest.fixture(scope='module')
def sample_module_logic(config):
    sample_base = 'logic'
    sample_module_name, sample_module_cfg = list(config[sample_base].items())[0]
    return sample_base, sample_module_name, sample_module_cfg

@pytest.fixture(scope="module")
def module_manager(qudi_instance):
    return qudi_instance.module_manager




def test_ranking_active_dependent_modules(module_manager, config,sample_module_logic):
    for base in ['gui', 'logic', 'hardware']:
        for module_name, module_cfg in list(config[base].items()):
            module_manager.add_module(module_name, base, module_cfg, allow_overwrite=False, emit_change=True )
    module_manager.start_all_modules()
    sample_base, sample_module_name, sample_module_cfg = sample_module_logic
    print( type(module_manager.modules[sample_module_name]))
    active_modules = module_manager.modules[sample_module_name].ranking_active_dependent_modules
    print(f'active dep modules for {sample_module_name} are {active_modules}')
    assert False

    

