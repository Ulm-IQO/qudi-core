# -*- coding: utf-8 -*-
"""
Class-based value converters ( cattrs hooks) for qudi.

Every converter is a subclass of `ValueConverter` that sets `target` to the class it
handles and implements `unstructure` and `structure`. `get_converter` discovers all
such subclasses in the `qudi.util.value_converters` namespace and registers them.


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

__all__ = ['ValueConverter', 'get_converter', 'structure', 'unstructure']

import functools
from abc import ABC, abstractmethod
from typing import Any
from types import MappingProxyType
from functools import partial
from cattrs import Converter

from qudi.util.module_finder import get_modules_from_ns, is_subclass


class ValueConverter(ABC):
    """Base cattrs hook class: set `target` and implement both directions."""

    target: type | None = None

    @abstractmethod
    def unstructure(self, obj: Any) -> Any:
        """Object -> primitives."""

    @abstractmethod
    def structure(self, value: Any, type_: type) -> Any:
        """Primitives -> object."""

    def register(self, converter: Converter) -> None:
        if not isinstance(self.target, type):
            raise TypeError(f'{type(self).__name__}.target must be a class, got {self.target!r}')
        converter.register_unstructure_hook(self.target, self.unstructure)
        converter.register_structure_hook(self.target, self.structure)


_is_converter_class = partial(is_subclass, base=ValueConverter)



@functools.cache
def _build() -> tuple[Converter, dict[type, type[ValueConverter]]]:
    """ Build a cattrs converter that automatically registers hooks(value converters) in the namespace, built once on first use.
    Also reutrns dict of registered value converters"""

    import qudi.util.value_converters as ns
    classes = get_modules_from_ns(ns, _is_converter_class, simple_module_name=False)

    # Guarding against multiple hooks(value converters) registered for the same target type
    owners: dict[type, type[ValueConverter]] = {}
    for cls in classes.values():
        target = cls.target
        if not isinstance(target, type):
            raise TypeError(f'{cls.__module__}.{cls.__qualname__}.target must be a class, '
                            f'got {target!r}')
        if target in owners:
            other = owners[target]
            raise TypeError(
                f'Conflicting value converters for {target.__qualname__}: '
                f'{other.__module__}.{other.__qualname__} and {cls.__module__}.{cls.__qualname__}'
            )
        owners[target] = cls

    converter = Converter()
    for cls in owners.values():
        cls().register(converter)
    return converter, owners

def get_converter() -> Converter:
    """Returns the built converter."""
    return _build()[0]

def registered_converters() -> MappingProxyType[type, type[ValueConverter]]:
    """Read-only mapping of target type to the ValueConverter class handling it."""
    return MappingProxyType(_build()[1])

def unstructure(obj: Any) -> Any:
    return get_converter().unstructure(obj)


def structure(value: Any, type_: type) -> Any:
    return get_converter().structure(value, type_)