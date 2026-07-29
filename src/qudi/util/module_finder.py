# -*- coding: utf-8 -*-
"""
This file contains shared helpers for discovering and importing plugin-style method/function classes 

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

import os
import sys
import inspect
import importlib
import logging
from logging import Logger
from collections.abc import Callable
from typing import List, Type, Dict, Any

from qudi.core import  Base
from qudi.util.helpers import iter_modules_recursive



def get_module_names_from_ns(namespace: object) -> List[str]:
        """
        Get list of module names from namespace
        """
        module_names = [mod_finder.name for mod_finder in
                        iter_modules_recursive(namespace.__path__, f'{namespace.__name__}.')]
        return list(dict.fromkeys(module_names))

def get_classes_in_module(module: object, predicate: Callable[[Any], bool] | None , simple_module_name: bool) -> Dict[str, Type[Base]]:
        """
        Get module, class pairs for a module
        
        Parameters
        ----------
        module
            module object
        predicate
            predicate to be satisfied
        simple_module_name
            boolean to indicate whether to fetch the module names without or with the absolute path of the module
            if True, the module names are simple (just the name of the module), if False, the module names are absolute paths.
        
        Returns
        -------
        dict
            dict of module name and its corresponding base class.
           
        """
        members = inspect.getmembers(module, predicate)
        if simple_module_name:
            return {name: cls for name, cls in members}  
        else:
            return {f'{module.__name__}.{name}': obj for name, obj in members if
                obj.__module__ == module.__name__}
        
def get_modules_from_ns(namespace: object, predicate: Callable[[Any], bool] | None = None, simple_module_name: bool = True, logger: Logger = None) -> Dict[str, Type[Base]]:
        """
        Get modules from a namespace
        
        Parameters
        ----------
         namespace
            namespace object
        predicate
            predicate to be satisfied
        simple_module_name
            boolean to indicate whether to fetch the module names without or with the absolute path of the module
            if True, the module names are simple (just the name of the module), if False, the module names are absolute paths.
        logger
            logger for the module
        
        Returns
        -------
        dict
            dict of module name and its corresponding base class.
           
        """
        modules = dict()
        for module_name in get_module_names_from_ns(namespace):
            try:
                module = importlib.import_module(module_name)
            except:
                if logger is None:
                     logger = logging.getLogger(__package__)

                logger.exception(f'Error during import of module "{module_name}"')
                continue
            modules.update(get_classes_in_module(module, predicate, simple_module_name))
        return modules


def iter_directory_module_names(path: str):
    """ Yield the top-level module names of all ``*.py`` files in a directory, adding that directory
    to ``sys.path`` so the modules become importable by their bare name.
    """
    module_names = [name[:-3] for name in os.listdir(path)
                    if os.path.isfile(os.path.join(path, name)) and name.endswith('.py')]
    if path not in sys.path:
        sys.path.append(path)
    yield from module_names


def get_modules_from_path(path: str, predicate:  Callable[[Any], bool] | None = None, *, reload=True) -> List[Type[Base]]:
    """ Collect all modules matching ``predicate`` from the loose ``*.py`` modules in a directory.
    """
    class_list = list()
    for module_name in iter_directory_module_names(path):
        module = importlib.import_module(str(module_name))
        if reload:
            module = importlib.reload(module)
        class_list.extend(cls for _, cls in inspect.getmembers(module, predicate))
    return class_list


def normalize_import_paths(paths: list| str, option_name: str = None, logger: Logger = None) -> List[str]:
    """ Coerce a ConfigOption import-path value into a validated list of existing directories.
    """
    path_list = list()
    if not paths:
        return path_list

    if isinstance(paths, str):
        paths = [paths]

    if isinstance(paths, (list, tuple, set)):
        for path in paths:
            if not os.path.exists(path):
                if logger is not None:
                    logger.error(f'Specified path "{path}" for import of {option_name} does not '
                                 f'exist.')
            else:
                path_list.append(path)
    elif logger is not None:
        logger.error(f'ConfigOption {option_name} needs to either be a string or a list of '
                     f'strings.')
    return path_list