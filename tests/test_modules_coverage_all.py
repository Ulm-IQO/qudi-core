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
from qudi.util.yaml import yaml_load
import pytest
from PySide2 import QtWidgets
import weakref
import coverage
import os
import time


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
    configuration = (yaml_load(CONFIG))
    return configuration


@pytest.fixture(scope="module")
def module_manager(qudi_instance):
    return qudi_instance.module_manager

    
@pytest.fixture(scope='module')
def sample_module_gui(config):
    sample_base = 'gui'
    sample_module_name, sample_module_cfg = list(config[sample_base].items())[0]
    return sample_base, sample_module_name, sample_module_cfg


def test_activate_module(module_manager, config,sample_module_gui):
        for base in ['gui', 'logic', 'hardware']:
            for module_name, module_cfg in list(config[base].items()):
                module_manager.add_module(module_name, base, module_cfg, allow_overwrite=False, emit_change=True )
        #_, sample_gui, _ = sample_module_gui
        #module_manager.activate_module(sample_gui)
        cov = coverage.Coverage()
        cov.start()
        gui_base = 'gui'
        for module_name, _ in list(config[gui_base].items()):
            print(module_name)
            
            
        
            module_manager.activate_module(module_name)
            
            assert module_manager.modules[module_name].is_active
            
            # Create a unique directory for each test function
            
            #module_manager.deactivate_module(module_name)

        cov.stop()
        test_dir =  os.path.join('coverage',"coverage_all_qudi")
        os.makedirs(test_dir, exist_ok=True)
        
        # Save the coverage report
        cov.html_report(directory=test_dir)
        cov.save()

        print(f"Coverage report saved to {test_dir}")
