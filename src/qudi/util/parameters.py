# -*- coding: utf-8 -*-
"""
This file contains utility methods to annotate arguments for which the user can potentially edit
values via GUI. These arguments are boiled down to simple builtin types that can be represented by
a GUI editor:
                            int: qudi.util.widgets.scientific_spinbox.ScienSpinBox
                          float: qudi.util.widgets.scientific_spinbox.ScienDSpinbox
                            str: PySide6.QtWidgets.QLineEdit
                        complex: qudi.util.widgets.literal_lineedit.ComplexLineEdit
                            set: qudi.util.widgets.literal_lineedit.SetLineEdit
                           dict: qudi.util.widgets.literal_lineedit.DictLineEdit
                           list: qudi.util.widgets.literal_lineedit.ListLineEdit
                          tuple: qudi.util.widgets.literal_lineedit.TupleLineEdit

Here defined are also custom generic types that can be used like any other type from
the typing module.
Arguments annotated with these types are represented with the following widgets:
    FilePath: PySide6.QtWidgets.QLineEdit

Any other type annotation that can not be mapped to a simple builtin or a custom generic type
(see above) will result in no corresponding widget (None).

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

__all__ = ['FilePath', 'RealNumber', 'ParameterWidgetMapper']

import inspect
import typing
from os import PathLike
from PySide6 import QtWidgets
from typing import Callable, Any, Set, FrozenSet, MutableSequence, Mapping, Tuple, Dict, Type, Union
from typing import get_origin, get_args, Iterable, Sequence

from qudi.util.helpers import is_complex_type, is_float_type, is_integer_type, is_string_type
from qudi.util.widgets.scientific_spinbox import ScienSpinBox, ScienDSpinBox
from qudi.util.widgets.literal_lineedit import ComplexLineEdit, TupleLineEdit, ListLineEdit
from qudi.util.widgets.literal_lineedit import SetLineEdit, DictLineEdit


FilePath = Union[str, bytes, PathLike]
RealNumber = Union[int, float]


class ParameterWidgetMapper:

    _type_widget_map = {int: ScienSpinBox,
                        float: ScienDSpinBox,
                        str: QtWidgets.QLineEdit,
                        PathLike: QtWidgets.QLineEdit,
                        complex: ComplexLineEdit,
                        set: SetLineEdit,
                        dict: DictLineEdit,
                        tuple: TupleLineEdit,
                        list: ListLineEdit}

    @classmethod
    def widgets_for_callable(cls, func: Callable) -> Dict[str, Union[Type[QtWidgets.QWidget], None]]:
        """ Returns QWidget classes for each parameter from the call signature of "func".
        See ParameterWidgetMapper.widget_for_parameter for more information.
        """
        sig = inspect.signature(func)
        return {name: cls.widget_for_parameter(param) for name, param in sig.parameters.items()}

    @classmethod
    def widget_for_parameter(cls, param: inspect.Parameter) -> Union[Type[QtWidgets.QWidget], None]:
        """ Tries to determine a suitable QWidget to represent the given parameter.
        If no type annotation is given for a parameter it will try to determine the type from the
        default value.
        If no (known) type can be determined, None will be returned.
        """
        # Try to deduce missing type annotation from default parameter type
        if param.annotation is inspect.Parameter.empty:
            if param.default is inspect.Parameter.empty:
                return None
            else:
                return cls.widget_from_value(param.default)
        else:
            return cls.widget_from_annotation(param.annotation)

    @classmethod
    def widget_from_value(cls, value: Any) -> Union[Type[QtWidgets.QWidget], None]:
        """ Tries to determine a suitable QWidget to represent the type of the given value.
        """
        normalized_type = cls._normalize_type(type(value))
        return cls._type_widget_map.get(normalized_type, None)

    @classmethod
    def widget_from_annotation(cls, annotation: Any) -> Union[Type[QtWidgets.QWidget], None]:
        """ Tries to determine a suitable QWidget to represent values of the given annotation type.
        """
        normalized_type = cls._annotation_to_type(annotation)
        return cls._type_widget_map.get(normalized_type, None)

    @staticmethod
    def _normalize_type(typ: Type) -> Type:
        """ Normalizes given type to a base/builtin type.
        Examples:
                      numpy.float32 -> float
            collections.OrderedDict -> dict
        """
        if is_string_type(typ):
            return str
        elif is_integer_type(typ):
            return int
        elif is_float_type(typ):
            return float
        elif is_complex_type(typ):
            return complex
        elif issubclass(typ, (bytes, PathLike)):
            return PathLike
        elif issubclass(typ, (Set, FrozenSet)):
            return set
        elif issubclass(typ, Mapping):
            return dict
        elif issubclass(typ, MutableSequence):
            return list
        elif issubclass(typ, (Tuple, Iterable, Sequence)):
            return tuple
        return None

    @classmethod
    def _annotation_to_type(cls, annotation: Any) -> Type:
        """ Converts a type annotation (e.g. from a callable signature) to a normalized type.
        See ParameterWidgetMapper._normalize_type for more information.
        """
        # If annotation is optional, call this method again on the first argument in order to get a
        # type
        if cls._is_optional_annotation(annotation):
            return cls._annotation_to_type(get_args(annotation)[0])

        if annotation == RealNumber:
            return float
        elif annotation == FilePath:
            return PathLike
        else:
            try:
                if inspect.isclass(annotation):
                    return cls._normalize_type(annotation)
                else:
                    return cls._normalize_type(get_origin(annotation))
            except TypeError:
                pass
        return None

    @staticmethod
    def _is_optional_annotation(annotation: Any) -> bool:
        """ Check if an annotation is optional, i.e. if it is typing.Union with two arguments,
        the second one being NoneType
        """
        if get_origin(annotation) == typing.Union:
            args = get_args(annotation)
            return len(args) == 2 and issubclass(args[1], type(None))
        return False
