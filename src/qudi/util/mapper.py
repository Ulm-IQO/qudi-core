# -*- coding: utf-8 -*-
"""
This file contains the Qudi mapper module.

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

__all__ = ['Converter', 'Mapper']

from PySide2.QtCore import QCoreApplication
from PySide2.QtCore import QThread
from PySide2.QtCore import QTimer
from PySide2.QtWidgets import QAbstractButton
from PySide2.QtWidgets import QAbstractSlider
from PySide2.QtWidgets import QComboBox
from PySide2.QtWidgets import QDoubleSpinBox
from PySide2.QtWidgets import QLineEdit
from PySide2.QtWidgets import QPlainTextEdit
from PySide2.QtWidgets import QSpinBox

import functools

SUBMIT_POLICY_AUTO = 0
"""automatically submit changes"""
SUBMIT_POLICY_MANUAL = 1
"""wait with submitting changes until submit() is called"""


class Converter:
    """
    Class for converting data between display and storage (i.e. widget and
    model).
    """
    def widget_to_model(self, data):
        """
        Converts data from the format given by the widget to the model data format.

        Parameters
        ----------
        data : object
            Data to be converted.

        Returns
        -------
        object
            Converted data.

        """
        return data

    def model_to_widget(self, data):
        """
        Converts data from the model format to the widget data format.

        Parameters
        ----------
        data : object
            Data to be converted from the model format to the widget format.

        Returns
        -------
        object
            Converted data in the widget format.

        """
        return data


class Mapper:
    """
    The Mapper connects a Qt widget for displaying and editing certain data
    types with a model property or setter and getter functions. The model can
    be e.g. a logic or a hardware module.

    Usage Example:
    ==============

    We assume to have a logic module which is connected to our GUI via a
    connector and we can access it by the `logic_module` variable. We
    further assume that this logic module has a string property called
    `some_value` and a signal `some_value_changed` which is emitted when the
    property is changed programmatically.
    In the GUI module we have defined a QLineEdit, e.g. by
    ```
    lineedit = QLineEdit()
    ```
    In the on_activate method of the GUI module, we define the following
    mapping between the line edit and the logic property:
    ```
    def on_activate(self):
        self.mapper = Mapper()
        self.mapper.add_mapping(self.lineedit, self.logic_module,
                'some_value', 'some_value_changed')
    ```
    Now, if the user changes the string in the lineedit, the property of the
    logic module is changed. If the logic module's property is changed
    programmatically, the change is automatically displayed in the GUI.

    If the GUI module is deactivated we should delete all mappings:
    ```
    def on_deactivate(self):
        self.mapper.clear_mapping()
    ```
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._submit_policy = SUBMIT_POLICY_AUTO
        self._mappings = {}

    def _get_property_from_widget(self, widget):
        """
        Returns the property name we determined from the widget's type.
        """
        if isinstance(widget, QAbstractButton):
            return 'checked'
        elif isinstance(widget, QComboBox):
            return 'currentIndex'
        elif isinstance(widget, QLineEdit):
            return 'text'
        elif (isinstance(widget, (QSpinBox,
                                  QDoubleSpinBox,
                                  QAbstractSlider))):
            return 'value'
        elif isinstance(widget, QPlainTextEdit):
            return 'plainText'
        else:
            raise TypeError(f'Property of widget {repr(widget)} could not be determined.')

    def add_mapping(self,
                    widget,
                    model,
                    model_getter,
                    model_property_notifier=None,
                    model_setter=None,
                    widget_property_name='',
                    widget_property_notifier=None,
                    converter=None):
        """
        Adds a mapping.

        Parameters
        ----------
        widget : QtWidget
            A widget displaying some data. You want to map this widget to model data.
        model : object
            Instance of a class holding model data (e.g. a logic or hardware module).
        model_getter : property/callable 
            Either a property holding the data to be displayed in widget or a getter method to retrieve data from the
            model was changed.
        model_property_notifier : Signal
            A signal that is fired when the data was changed. If None then data changes are not monitored and the
            widget is not updated. Default is None.
        model_setter : callable
            A setter method which is called to set data to the model. If model_getter is a property the setter can be
            determined from this property and model_setter is ignored if it is None. If it is not None always this
            callable is used. Default is None.
        widget_property_name : str
            The name of the pyqtProperty of the widget used to map the data. If it is an empty string the relevant
            property is guessed from the widget's type. Default is ''.
        widget_property_notifier : Signal
            Notifier signal which is fired by the widget when the data changed. If None, this is determined directly
            from the property. Example usage: QLineEdit().editingFinished. Default is None.
        converter : Converter
            Converter instance for converting data between widget display and model. Default is None.
        """
        # guess widget property if not specified
        if widget_property_name == '':
            widget_property_name = self._get_property_from_widget(widget)

        # define key of mapping
        key = (widget, widget_property_name)

        # check if already exists
        if key in self._mappings:
            raise RuntimeError(
                f'Property {widget_property_name} of widget {repr(widget)} already mapped.'
            )

        # check if widget property is available
        index = widget.metaObject().indexOfProperty(widget_property_name)
        if index == -1:
            raise RuntimeError(
                f'Property "{widget_property_name}" of widget "{widget.__class__.__name__}" not '
                f'available.'
            )

        meta_property = widget.metaObject().property(index)

        # widget property notifier
        if widget_property_notifier is None:
            # check that widget property as a notify signal
            if not meta_property.hasNotifySignal():
                raise RuntimeError(
                    f'Property "{widget_property_name}" of widget "{widget.__class__.__name__}" '
                    f'has no notify signal.'
                )

            widget_property_notifier = getattr(
                widget,
                meta_property.notifySignal().name().data().decode('utf8'))

        # check that widget property is readable
        if not meta_property.isReadable():
            raise RuntimeError(
                f'Property "{widget_property_name}" of widget "{widget.__class__.__name__}" is not '
                f'readable.'
            )
        widget_property_getter = meta_property.read
        # check that widget property is writable if requested
        if not meta_property.isWritable():
            raise RuntimeError(
                f'Property "{widget_property_name}" of widget "{widget.__class__.__name__}" is not '
                f'writable.'
            )
        widget_property_setter = meta_property.write

        if isinstance(model_getter, str):
            # check if it is a property
            attr = getattr(model.__class__, model_getter, None)
            if attr is None:
                raise AttributeError(f'Model has no attribute "{model_getter}"')
            if isinstance(attr, property):
                # retrieve getter from property
                model_property_name = model_getter
                model_getter = functools.partial(attr.fget, model)
                # if no setter was specified, get it from the property
                if model_setter is None:
                    model_setter = functools.partial(attr.fset, model)
                    if model_getter is None:
                        raise AttributeError(
                            f'Attribute "{model_property_name}" of model is readonly.'
                        )
            else:
                # getter is not a property. Check if it is a callable.
                model_getter_name = model_getter
                model_getter = getattr(model, model_getter)
                if not callable(model_getter):
                    raise AttributeError(
                        f'Attribute "{model_getter_name}" of model is not callable.'
                    )
        if isinstance(model_setter, str):
            model_setter_name = model_setter
            model_setter = getattr(model, model_setter)
            if not callable(model_setter):
                raise AttributeError(f'Attribute "{model_setter_name}" of model is not callable')
        if isinstance(model_property_notifier, str):
            model_property_notifier = getattr(model, model_property_notifier)

        # connect to widget property notifier
        widget_property_notifier_slot = functools.partial(
            self._on_widget_property_notification, key)
        widget_property_notifier.connect(widget_property_notifier_slot)

        # if model_notify_signal was specified, connect to it
        model_property_notifier_slot = None
        if model_property_notifier is not None:
            model_property_notifier_slot = functools.partial(
                self._on_model_notification, key)
            model_property_notifier.connect(model_property_notifier_slot)
        # save mapping
        self._mappings[key] = {
            'widget_property_name': widget_property_name,
            'widget_property_getter': widget_property_getter,
            'widget_property_setter': widget_property_setter,
            'widget_property_notifier': widget_property_notifier,
            'widget_property_notifier_slot': widget_property_notifier_slot,
            'widget_property_notifications_disabled': False,
            'model': model,
            'model_property_setter': model_setter,
            'model_property_getter': model_getter,
            'model_property_notifier': model_property_notifier,
            'model_property_notifier_slot': model_property_notifier_slot,
            'model_property_notifications_disabled': False,
            'converter': converter}

    def _on_widget_property_notification(self, key, *args):
        """
        Event handler for widget property change notification. Used with
        functools.partial to get the widget as first parameter.

        Parameters
        ----------
        key : (QtWidget, str)
            The key consisting of widget and property name, the notification signal was emitted from.
        args*: list
            List of event parameters.
        """
        widget, widget_property_name = key
        if self._mappings[key]['widget_property_notifications_disabled']:
            return
        if self._submit_policy == SUBMIT_POLICY_AUTO:
            self._mappings[key][
                'model_property_notifications_disabled'] = True
            try:
                # get value
                value = self._mappings[key]['widget_property_getter'](
                    widget)
                # convert it if requested
                if self._mappings[key]['converter'] is not None:
                    value = self._mappings[key][
                        'converter'].widget_to_model(value)
                # set it to model
                self._mappings[key]['model_property_setter'](value)
            finally:
                self._mappings[key][
                    'model_property_notifications_disabled'] = False
        else:
            pass

    def _on_model_notification(self, key, *args):
        """
        Event handler for model data change notification. Used with
        functools.partial to get the widget as first parameter.

        Parameters
        ----------
        key : (QtWidget, str)
            The key consisting of widget and property name the notification signal was emitted from.
        args* : list
            List of event parameters
        """
        widget, widget_property_name = key
        mapping = self._mappings[key]
        # get value from model
        value = self._mappings[key]['model_property_getter']()

        # are updates disabled?
        if self._mappings[key]['model_property_notifications_disabled']:
            # but check if value has changed first
            # get value from widget
            value_widget = self._mappings[key]['widget_property_getter'](
                widget)
            # convert it if requested
            if self._mappings[key]['converter'] is not None:
                value_widget = self._mappings[key][
                    'converter'].widget_to_model(value_widget)
            # accept changes, stop if nothing has changed
            if value == value_widget:
                return

        # convert value if requested
        if self._mappings[key]['converter'] is not None:
            value = self._mappings[key]['converter'].model_to_widget(value)

        # update widget
        self._mappings[key][
            'widget_property_notifications_disabled'] = True
        try:
            self._mappings[key]['widget_property_setter'](widget, value)
        finally:
            self._mappings[key][
                'widget_property_notifications_disabled'] = False

    def clear_mapping(self):
        """
        Clears all mappings.
        """
        # convert iterator to list because the _mappings dictionary will
        # change its size during iteration
        for key in list(self._mappings.keys()):
            self.remove_mapping(key)

    def remove_mapping(self, widget, widget_property_name=''):
        """
        Removes the mapping which maps the QtWidget widget to some model data.

        Parameters
        ----------
        widget : QtWidget/(QtWidget, str)
            Widget the mapping is attached to or a tuple containing the widget and the widget's property name.
        widget_property_name : str
            Name of the property of the widget we are dealing with. If '' it will be determined from the widget.
            Default is ''.
        """
        if isinstance(widget, tuple):
            widget, widget_property_name = widget
        # guess widget property if not specified
        if widget_property_name == '':
            widget_property_name = self._get_property_from_widget(widget)
        # define key
        key = (widget, widget_property_name)
        # check that key has a mapping
        if not key in self._mappings:
            raise RuntimeError(f'Widget "{repr(widget)}" is not mapped.')
        # disconnect signals
        self._mappings[key]['widget_property_notifier'].disconnect(
            self._mappings[key]['widget_property_notifier_slot'])
        if self._mappings[key]['model_property_notifier'] is not None:
            self._mappings[key]['model_property_notifier'].disconnect(
                self._mappings[key]['model_property_notifier_slot'])
        # remove from dictionary
        del self._mappings[key]

    @property
    def submit_policy(self):
        """
        Returns the submit policy.
        """
        return self._submit_policy

    @submit_policy.setter
    def submit_policy(self, policy):
        """
        Sets submit policy.

        Submit policy can either be SUBMIT_POLICY_AUTO or
        SUBMIT_POLICY_MANUAL. If the submit policy is auto then changes in
        the widgets are automatically submitted to the model. If manual
        call submit() to submit it.

        Parameters
        ----------
        policy : enum 
            Submit policy.
        """
        if policy not in [SUBMIT_POLICY_AUTO, SUBMIT_POLICY_MANUAL]:
            raise ValueError(f'Unknown submit policy "{policy}"')
        self._submit_policy = policy

    def submit(self):
        """
        Submits the current values stored in the widgets to the models.
        """
        # make sure it is called from main thread
        if (not QThread.currentThread() == QCoreApplication.instance(
        ).thread()):
            QTimer.singleShot(0, self.submit)
            return

        submit_policy = self._submit_policy
        self.submit_policy = SUBMIT_POLICY_AUTO
        try:
            for key in self._mappings:
                self._on_widget_property_notification(key)
        finally:
            self.submit_policy = submit_policy

    def revert(self):
        """
        Takes the data stored in the models and displays them in the widgets.
        """
        # make sure it is called from main thread
        if (not QThread.currentThread() == QCoreApplication.instance(
        ).thread()):
            QTimer.singleShot(0, self.revert)
            return

        for key in self._mappings:
            self._on_model_notification(key)
