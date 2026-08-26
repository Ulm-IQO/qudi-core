# -*- coding: utf-8 -*-
"""
StatusVar object for qudi modules to allow storing of application status variables on disk.
These variables get stored during deactivation of qudi modules and loaded back in during activation.

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

__all__ = ['StatusVar']

import copy
import inspect
from collections.abc import Callable
from typing import Any, Generic, TypeVar, cast

T = TypeVar('T')


class StatusVar(Generic[T]):
    """This class defines a status variable that is loaded before activation and saved after
    deactivation.
    """

    def __init__(self, name: str | None = None, default: T | None = None, *,
                 constructor: Callable[..., T] | None = None,
                 representer: Callable[..., Any] | None = None):
        """
        Parameters
        ----------
        name : str
            Identifier of the status variable when stored.
        default : Any
            Default value for the status variable when a saved version is not present.
        constructor : callable
            Constructor function for the variable; use for type checks or conversion.
        representer : callable
            Representer function for the status variable; use for saving conversion.
        """
        self.name = name
        self.default = default
        self.constructor_function: Callable[[Any, Any], T] | None = None
        self.representer_function: Callable[[Any, T], Any] | None = None
        if constructor is not None:
            self.constructor(constructor)
        if representer is not None:
            self.representer(representer)

    def __get__(self, instance, owner) -> T:
        return self

    def __set_name__(self, owner, name):
        if self.name is None:
            self.name = name

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memodict={}):
        return self.copy()

    def copy(self, **kwargs) -> StatusVar[T]:
        """Create a new instance of StatusVar with copied and updated values.

        Parameters
        ----------
        **kwargs : dict
            Additional or overridden parameters for the constructor of this class.
        """
        newargs = {'name': self.name,
                   'default': copy.deepcopy(self.default),
                   'constructor': self.constructor_function,
                   'representer': self.representer_function}
        newargs.update(kwargs)
        return cast(StatusVar[T], StatusVar(**newargs))

    def constructor(self, func: Callable[..., T]) -> Callable[..., T]:
        """This is the decorator for declaring constructor function for this StatusVar.

        Parameters
        ----------
        func : callable
            Constructor function for this StatusVar.

        Returns
        -------
        callable
            The original function so this can be used as a decorator.
        """
        self.constructor_function = self._assert_func_signature(func)
        return func

    def representer(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """This is the decorator for declaring a representer function for this StatusVar.

        Parameters
        ----------
        func : callable
            Representer function for this StatusVar.

        Returns
        -------
        callable
            The original function so this can be used as a decorator.
        """
        self.representer_function = self._assert_func_signature(func)
        return func

    @staticmethod
    def _assert_func_signature(func: Callable[..., Any]) -> Callable[..., Any]:
        assert callable(func), 'StatusVar constructor/representer must be callable'
        params = tuple(inspect.signature(func).parameters)
        assert 0 < len(params) < 3, 'StatusVar constructor/representer must be function with ' \
                                    '1 (static) or 2 (bound method) parameters.'
        if len(params) == 1:
            def wrapper(instance, value):
                return func(value)

            return wrapper
        return func

    def check_value_type(self, value: Any) -> tuple[Any, str | None]:
        """ Reconcile a loaded status variable value against this StatusVar's default.
        Missing dict keys are backfilled from the default; values whose type does not
        match the default's are replaced by the default.
        """
        default = self.default
        messages: list[str] = []

        # 1. dict handling: backfill missing keys, then per-value type reconciliation
        if isinstance(value, dict) and isinstance(default, dict):
            value, missing_keys = self._merge_defaults(value, default)
            if missing_keys:
                messages.append(f"status variable '{self.name}' has missing keys "
                                f"{missing_keys} which are loaded with default values")
            value, value_msgs = self._reconcile_dict_value_types(value, default, self.name)
            messages.extend(value_msgs)

        # 2. top-level type comparison -> substitute the default on mismatch
        if (default is not None and value is not None
                and not self._types_match(type(default), type(value))):
            messages.append(f"status variable '{self.name}' loaded as type "
                            f"'{type(value).__name__}' but its default is of type "
                            f"'{type(default).__name__}';")
            value = copy.deepcopy(default)

        return value, ('; '.join(messages) if messages else None)

    @classmethod
    def _reconcile_dict_value_types(cls, loaded: dict, default: dict, path: str) -> tuple[dict, list]:
        """ Recursively compare the type of each value under a shared key against the
        default; where they differ, substitute it with the default value.
        """
        reconciled = dict(loaded)
        messages = []
        for key, default_value in default.items():
            if key not in reconciled:
                continue 
            loaded_value = reconciled[key]
            if default_value is None or loaded_value is None:
                continue 
            if isinstance(loaded_value, dict) and isinstance(default_value, dict):
                reconciled[key], sub = cls._reconcile_dict_value_types(
                    loaded_value, default_value, f"{path}.{key}")
                messages.extend(sub)
            elif not cls._types_match(type(default_value), type(loaded_value)):
                messages.append(f"key '{path}.{key}' loaded as type "
                                f"'{type(loaded_value).__name__}' but default is of type "
                                f"'{type(default_value).__name__}';")
                reconciled[key] = copy.deepcopy(default_value)
        return reconciled, messages

    @staticmethod
    def _types_match(expected: type, actual: type) -> bool:
        if actual is expected:
            return True
        numeric = (int, float)
        return (expected in numeric and actual in numeric
                and expected is not bool and actual is not bool)

    @staticmethod
    def _merge_defaults(loaded: dict, default: dict) -> tuple[dict, list]:
        """Fill the missing keys in the loaded dict with default dict
        """
        merged = dict(loaded)
        missing_keys = []
        for key, default_value in default.items():
            if key not in merged:
                missing_keys.append(key)
                merged[key] = copy.deepcopy(default_value)
            elif isinstance(merged[key], dict) and isinstance(default_value, dict):
                merged[key], _ = StatusVar._merge_defaults(merged[key], default_value)
        return merged, missing_keys

  