import pytest
from qudi.core import application,modulemanager
from qudi.util.yaml import yaml_load
from PySide2 import QtWidgets
import weakref
import logging
import sys 

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
def qudi_instance():
    instance = application.Qudi.instance()
    if instance is None:
        instance = application.Qudi(config_file=CONFIG)
    instance_weak = weakref.ref(instance)
    return instance_weak()

@pytest.fixture(scope="module")
def module_manager(qudi_instance):
    return qudi_instance.module_manager

@pytest.fixture(scope='module')
def config():
    configuration = (yaml_load(CONFIG))
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



@pytest.fixture(scope='module')
def teardown_modules(qudi_instance):
    yield
    if qudi_instance.module_manager.modules:
        for module in qudi_instance.module_manager.modules:
            qudi_instance.module_manager.remove_module(module,ignore_missing= True)


def pytest_sessionfinish(session, exitstatus):
    instance = application.Qudi.instance()
    logging.shutdown()
    if instance is not None:
        if instance.is_running:
            instance.quit()
        del instance

