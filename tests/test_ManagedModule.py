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
from PySide2.QtCore import QTimer
import weakref


CONFIG = 'C:/qudi/qudi-core/tests/dummy.cfg'
CONFIG = 'C:/qudi/default_2.cfg'


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

@pytest.fixture(scope='module')
def sample_module_hardware(config):
    sample_base = 'hardware'
    sample_module_name, sample_module_cfg = list(config[sample_base].items())[0]
    return sample_base, sample_module_name, sample_module_cfg

@pytest.fixture(scope="module")
def module_manager(qudi_instance):
    return qudi_instance.module_manager




def test_ranking_active_dependent_modules(module_manager, config,sample_module_hardware, sample_module_logic, sample_module_gui):
    for base in ['gui', 'logic', 'hardware']:
        for module_name, module_cfg in list(config[base].items()):
            module_manager.add_module(module_name, base, module_cfg, allow_overwrite=False, emit_change=True )
    module_manager.start_all_modules()
    _, sample_hardware, _ = sample_module_hardware
    _, sample_logic, _ = sample_module_logic
    _, sample_gui, _ = sample_module_gui

    active_dep_modules = module_manager.modules[sample_hardware].ranking_active_dependent_modules
    active_dep_modules = [ref() for ref in active_dep_modules]
    print(f'active dep modules for {sample_hardware} are {active_dep_modules}')
    #assert module_manager.modules[sample_logic] in active_dep_modules
    assert module_manager.modules[sample_gui] in active_dep_modules
    module_manager.clear()

def test_activate(module_manager, config, sample_module_hardware, sample_module_logic, sample_module_gui,qtbot):
        for base in ['gui', 'logic', 'hardware']:
            for module_name, module_cfg in list(config[base].items()):
                module_manager.add_module(module_name, base, module_cfg, allow_overwrite=False, emit_change=True )
        
        _, sample_hardware, _ = sample_module_hardware
        _, sample_logic, _ = sample_module_logic
        _, sample_gui, _ = sample_module_gui
        hardware_managed_module = module_manager.modules[sample_hardware]
        with qtbot.waitSignal( hardware_managed_module.sigStateChanged) as blockers:
            hardware_managed_module.activate( )
        emitted_signal = blockers.args


    

