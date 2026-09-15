# -*- coding: utf-8 -*-
"""
Class-based cattrs hooks for qudi.

Every hook is a subclass of `Hook` that sets `target` to the class it
handles and implements `unstructure` and/or `structure`.

And a converter class that automatically registers all such hooks.

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

from __future__ import annotations

import inspect
from abc import abstractmethod
from typing import Any
from cattrs import Converter


from qudi.util.module_finder import get_modules_from_ns
__all__ = ['Hook', 'CattrsConverter']



class Hook:
    """Base class for a single cattrs hook.

    Subclasses set `target` to the concrete class they handle and override
    `unstructure`, `structure`

    """

    target: type | None = None

    @abstractmethod
    def unstructure(self, obj: Any) -> Any:
        """Object -> primitive. Override to provide an unstructure hook."""
        raise NotImplementedError(f'{type(self).__name__} does not implement unstructure()')

    @abstractmethod
    def structure(self, value: Any, type_: type) -> Any:
        """Primitive -> object. Override to provide a structure hook."""
        raise NotImplementedError(f'{type(self).__name__} does not implement structure()')


    def register(self, converter: Converter) -> None:
        """Register whichever direction(s) this hook implements on `converter`."""
        if not isinstance(self.target, type):
            raise TypeError(
                f'{type(self).__name__}.target must be a class, got {self.target!r}'
            )
        converter.register_unstructure_hook(self.target, self.unstructure)
        converter.register_structure_hook(self.target, self.structure)




class CattrsConverter:
    """
    Cattrs converter class that registers defined hooks
    """

    def __init__(self):
        self._hooks: list[Hook] = self.get_hooks()
        self._converter = Converter()
        self.register_hooks()

    def get_hooks(self):
        import qudi.util.hooks as default_ns
        hooks = list(get_modules_from_ns(default_ns, self.is_hook_class,
                                                        ).values())
        return hooks

    def is_hook_class(self, obj: Any) -> bool:
        return inspect.isclass(obj) and Hook in obj.mro() and obj is not Hook

    def register_hooks(self) :
        for hook in self._hooks:
            hook().register(self._converter)

    @property
    def hooks(self) -> tuple[Hook, ...]:
        return tuple(self._hooks)
    
    @property
    def converter(self) -> Converter:
        return self._converter


