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



def test_add_module( module_manager, sample_module_gui, qtbot):
    '''
    Test the add_module function if it correctly adds modules
    Parameters
    ----------
    module_manager : ModuleManager
        This argument does something.
    ...

    Returns
    -------
    None
    '''
    sample_base, sample_module_name, sample_module_cfg = sample_module_gui    
    assert sample_module_name not in module_manager.module_names

    with qtbot.waitSignal( module_manager.sigManagedModulesChanged) as blockers:
        module_manager.add_module(sample_module_name, sample_base, sample_module_cfg, emit_change=True )
    emitted_signal = blockers.args
    assert sample_module_name in emitted_signal[0]

    assert sample_module_name in module_manager.module_names  
    assert isinstance(module_manager.modules[sample_module_name], modulemanager.ManagedModule)  
    

def test_remove_module(module_manager, sample_module_gui, qtbot):
    sample_base, sample_module_name, sample_module_cfg = sample_module_gui
    assert sample_module_name in module_manager.module_names 

    with qtbot.waitSignal( module_manager.sigManagedModulesChanged) as blockers:
        module_manager.remove_module(sample_module_name, emit_change=True )
    emitted_signal = blockers.args
    assert sample_module_name not in emitted_signal[0] 

    assert sample_module_name not in module_manager.module_names

    
def test_refresh_module_links(module_manager, sample_module_gui, sample_module_logic):
    sample_base, sample_module_name, sample_module_cfg = sample_module_gui  
    # Adding a sample gui module   
    gui_module = modulemanager.ManagedModule(module_manager._qudi_main_ref,sample_module_name, sample_base, sample_module_cfg)
    module_manager._modules[sample_module_name] = gui_module

    sample_base, sample_module_name, sample_module_cfg = sample_module_logic  
    # Adding a sample logic module to check if refresh links works  
    logic_module = modulemanager.ManagedModule(module_manager._qudi_main_ref,sample_module_name, sample_base, sample_module_cfg)
    module_manager._modules[sample_module_name] = logic_module


    module_manager.refresh_module_links()

    #Checking whether links have been refreshed, if yes , the logic module should be in required modules list for the gui module
    gui_required_modules = [ref() for ref in gui_module.required_modules]
    assert logic_module in gui_required_modules

    # And the GUI module should be in dependent modules list of logic module
    logic_dependent_modules = [ref() for ref in logic_module.dependent_modules]
    assert gui_module in logic_dependent_modules


def test_ranking_active_dependent_modules(module_manager, config):
    for base in ['gui', 'logic', 'hardware']:
        for module_name, module_cfg in config[base].items():
            module_manager.add_module(module_name, base, module_cfg, allow_overwrite=True, emit_change=True )
            #active_modules = module_manager.modules[].ranking_active_dependent_modules()
            print(module_manager.modules)

    

