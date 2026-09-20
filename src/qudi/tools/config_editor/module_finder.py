# -*- coding: utf-8 -*-
"""

"""

__all__ = ['ModuleFinder', 'QudiModules']

import inspect
import logging
from typing import List, Type, Dict, Iterable

from qudi.core import Connector, ConfigOption, Base, LogicBase, GuiBase
from qudi.util.module_finder import get_modules_from_ns
from qudi.util.helpers import iter_modules_recursive


log = logging.getLogger(__package__)


class ModuleFinder:
    """
    """
    @staticmethod
    def is_qudi_module(obj: type) -> bool:
        if obj in [Base, LogicBase, GuiBase]:
            return False
        return inspect.isclass(obj) and issubclass(obj, Base) and not inspect.isabstract(obj)

    @classmethod
    def get_qudi_modules_from_ns(cls, namespace: object, simple_module_name: bool = False) -> Dict[str, Type[Base]]:
        """
        Get qudi modules from a namespace

        Parameters
        ----------
        namespace
            namespace object
        simple_module_name
            boolean to indicate whether to fetch the module names without or with the absolute path of the module
            Here it is set to False by default as the absolute path is needed.
        Returns
        -------
        dict
            dict of module name and its corresponding base class .
        """
        qudi_modules = get_modules_from_ns(namespace, cls.is_qudi_module, simple_module_name, logger=log)
        return qudi_modules

    @classmethod
    def get_qudi_modules(cls) -> Dict[str, Dict[str, Type[Base]]]:
        try:
            import qudi.gui as _gui_ns
        except ImportError:
            _gui_ns = None
        try:
            import qudi.logic as _logic_ns
        except ImportError:
            _logic_ns = None
        try:
            import qudi.hardware as _hardware_ns
        except ImportError:
            _hardware_ns = None
        modules = dict()
        if _gui_ns is not None:
            modules.update(cls.get_qudi_modules_from_ns(_gui_ns))
        if _logic_ns is not None:
            modules.update(cls.get_qudi_modules_from_ns(_logic_ns))
        if _hardware_ns is not None:
            modules.update(cls.get_qudi_modules_from_ns(_hardware_ns))
        return modules


class QudiModules:
    """
    """

    def __init__(self):
        # import all qudi module classes if possible (log all errors upon import)
        self._qudi_modules = {mod[5:] if mod.startswith('qudi.') else mod: cls for mod, cls in
                              ModuleFinder.get_qudi_modules().items()}
        # Collect all connectors for all modules
        self._module_connectors = {
            mod: list(cls._meta['connectors'].values()) for mod, cls in self._qudi_modules.items()
        }
        # Get for each connector in each module compatible modules to connect to
        self._module_connectors_compatible_modules = {
            mod: self._modules_for_connectors(conn) for mod, conn in self._module_connectors.items()
        }
        # Get all ConfigOptions for all modules
        self._module_config_options = {
            mod: list(cls._meta['config_options'].values()) for mod, cls in
            self._qudi_modules.items()
        }

    def _modules_for_connectors(self, connectors: Iterable[Connector]) -> Dict[str, List[str]]:
        return {conn.name: self._modules_for_connector(conn) for conn in connectors}

    def _modules_for_connector(self, connector: Connector) -> List[str]:
        interface = connector.interface
        bases = {mod: {c.__name__ for c in cls.mro()} for mod, cls in self._qudi_modules.items()}
        return list(mod for mod, base_names in bases.items() if interface in base_names)

    @property
    def available_modules(self) -> List[str]:
        return list(self._qudi_modules)

    def module_connectors(self, module: str) -> List[Connector]:
        return self._module_connectors[module].copy()

    def module_connector_targets(self, module: str) -> Dict[str, List[str]]:
        return {k: v.copy() for k, v in self._module_connectors_compatible_modules[module].items()}

    def module_config_options(self, module: str) -> List[ConfigOption]:
        return self._module_config_options[module].copy()
