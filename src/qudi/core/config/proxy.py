# -*- coding: utf-8 -*-

"""
Proxy objects for validating data access to a qudi configuration tree (or any mapping in fact).

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

__all__ = ['MappingProxy', 'SequenceProxy', 'SetProxy']

from typing import Any, Callable
from collections.abc import MutableMapping, MutableSequence, MutableSet

from .validator import ValidationError


class MappingProxy(MutableMapping):
    """ Proxy object for mapping type data access with change validation.
    """

    def __init__(self, mapping: MutableMapping, validation_callback: Callable) -> None:
        if not isinstance(mapping, MutableMapping):
            raise TypeError('MappingProxy can only map registered MutableMapping and dict '
                            'instances')
        if not callable(validation_callback):
            raise TypeError('"validation_callback" parameter must be a callable without mandatory '
                            'arguments')
        self._mapping = mapping
        self._validation_callback = validation_callback

    def __getitem__(self, key):
        item = self._mapping[key]
        if isinstance(item, MutableMapping):
            return MappingProxy(item, self._validation_callback)
        if isinstance(item, MutableSequence):
            return SequenceProxy(item, self._validation_callback)
        if isinstance(item, MutableSet):
            return SetProxy(item, self._validation_callback)
        return item

    def __setitem__(self, key, value):
        old_value = self._mapping[key]
        self._mapping[key] = value
        try:
            self._validation_callback()
        except ValidationError:
            self._mapping[key] = old_value
            raise

    def __delitem__(self, key):
        old_value = self._mapping[key]
        del self._mapping[key]
        try:
            self._validation_callback()
        except ValidationError:
            self._mapping[key] = old_value
            raise

    def __iter__(self):
        return iter(self._mapping)

    def __len__(self) -> int:
        return len(self._mapping)


class SequenceProxy(MutableSequence):
    """ Proxy object for sequence type data access with change validation.
    """

    def __init__(self, sequence: MutableSequence, validation_callback: Callable) -> None:
        if not isinstance(sequence, MutableSequence):
            raise TypeError('SequenceProxy can only map registered MutableSequence and list '
                            'instances')
        if not callable(validation_callback):
            raise TypeError('"validation_callback" parameter must be a callable without mandatory '
                            'arguments')
        self._sequence = sequence
        self._validation_callback = validation_callback

    def __getitem__(self, index) -> Any:
        item = self._sequence[index]
        if isinstance(item, MutableMapping):
            return MappingProxy(item, self._validation_callback)
        if isinstance(item, MutableSequence):
            return SequenceProxy(item, self._validation_callback)
        if isinstance(item, MutableSet):
            return SetProxy(item, self._validation_callback)
        return item

    def __setitem__(self, index, value) -> None:
        old_value = self._sequence[index]
        self._sequence[index] = value
        try:
            self._validation_callback()
        except ValidationError:
            self._sequence[index] = old_value
            raise

    def __delitem__(self, index) -> None:
        old_value = self._sequence[index]
        del self._sequence[index]
        try:
            self._validation_callback()
        except ValidationError:
            self._sequence.insert(index, old_value)
            raise

    def __len__(self) -> int:
        return len(self._sequence)

    def insert(self, index: int, value: Any) -> None:
        self._sequence.insert(index, value)
        try:
            self._validation_callback()
        except ValidationError:
            del self._sequence[index]
            raise


class SetProxy(MutableSet):
    """ Proxy object for set type data access with change validation.
    """

    def __init__(self, set: MutableSet, validation_callback: Callable) -> None:
        if not isinstance(set, MutableSet):
            raise TypeError('SetProxy can only map registered MutableSet and set instances')
        if not callable(validation_callback):
            raise TypeError('"validation_callback" parameter must be a callable without mandatory '
                            'arguments')
        self._set = set
        self._validation_callback = validation_callback

    def __contains__(self, item) -> bool:
        return item in self._set

    def __iter__(self):
        return iter(self._set)

    def __len__(self) -> int:
        return len(self._set)

    def add(self, value) -> None:
        if value in self._set:
            return
        self._set.add(value)
        try:
            self._validation_callback()
        except ValidationError:
            self._set.discard(value)
            raise

    def discard(self, value) -> None:
        try:
            self._set.remove(value)
        except KeyError:
            return
        try:
            self._validation_callback()
        except ValidationError:
            self._set.add(value)
            raise
