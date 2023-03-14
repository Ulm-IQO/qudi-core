# -*- coding: utf-8 -*-
"""
Definition of various metaclasses

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

__all__ = ['ABCQObjectMeta', 'QObjectMeta', 'QudiObjectMeta', 'ABCQObject', 'QudiObject']

from abc import ABCMeta
from PySide2.QtCore import QObject, Signal
from qudi.core.statusvariable import StatusVar
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption


QObjectMeta = type(QObject)


class ABCQObjectMeta(ABCMeta, QObjectMeta):
    """ Metaclass for abstract QObject subclasses.
    """

    def __new__(mcs, name, bases, attributes):
        cls = super(ABCQObjectMeta, mcs).__new__(mcs, name, bases, attributes)
        # Compute set of abstract method names
        abstracts = {
            attr_name for attr_name, attr in attributes.items() if \
            getattr(attr, '__isabstractmethod__', False)
        }
        for base in bases:
            for attr_name in getattr(base, '__abstractmethods__', set()):
                attr = getattr(cls, attr_name, None)
                if getattr(attr, '__isabstractmethod__', False):
                    abstracts.add(attr_name)
        cls.__abstractmethods__ = frozenset(abstracts)
        return cls


class QudiObjectMeta(ABCQObjectMeta):
    """ General purpose metaclass for abstract QObject subclasses that include qudi meta attributes
    (Connector, StatusVar, ConfigOption).
    Collects all meta attributes in new "_meta" class variable for easier access.
    Also collects QtCore.Signal attribute names for easier maintenance and access.
    """
    def __new__(mcs, name, bases, attributes):
        cls = super().__new__(mcs, name, bases, attributes)

        # Collect qudi module meta attributes (Connector, StatusVar, ConfigOption) and put them
        # in the class variable dict "_meta" for easy bookkeeping and access.
        base_meta = getattr(cls, '_meta', dict())  # extend shallow copy of _meta dicts if existent

        connectors = base_meta.get('connectors', dict()).copy()
        status_vars = base_meta.get('status_variables', dict()).copy()
        config_opt = base_meta.get('config_options', dict()).copy()
        signals = base_meta.get('signals', dict()).copy()
        for attr_name, attr in cls.__dict__.items():
            if isinstance(attr, Connector):
                connectors[attr_name] = attr
            elif isinstance(attr, StatusVar):
                status_vars[attr_name] = attr
            elif isinstance(attr, ConfigOption):
                config_opt[attr_name] = attr
            elif isinstance(attr, Signal):
                signals[attr_name] = attr_name

        cls._meta = {'connectors'      : connectors,
                     'status_variables': status_vars,
                     'config_options'  : config_opt,
                     'signals'         : signals}
        return cls


class ABCQObject(QObject, metaclass=ABCQObjectMeta):
    """ Base class for an abstract QObject.
    This is necessary because of a known bug in PySide2(6).
    See: https://bugreports.qt.io/browse/PYSIDE-1434 for more details
    """
    def __new__(cls, *args, **kwargs):
        abstract = getattr(cls, '__abstractmethods__', frozenset())
        if abstract:
            raise TypeError(f'Can\'t instantiate abstract class "{cls.__name__}" '
                            f'with abstract methods {set(abstract)}')
        return super().__new__(cls, *args, **kwargs)


class QudiObject(ABCQObject, metaclass=QudiObjectMeta):
    pass
