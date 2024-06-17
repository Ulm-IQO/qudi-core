import qudi.util.fit_models as _fit_models_ns
from qudi.util.helpers import iter_modules_recursive

import importlib
import logging
import inspect
import lmfit
import numpy as np
from PySide2 import QtCore
from typing import Iterable, Optional, Mapping, Union

import qudi.util.fit_models as _fit_models_ns
from qudi.util.mutex import Mutex
from qudi.util.units import create_formatted_output
from qudi.util.helpers import iter_modules_recursive
from qudi.util.fit_models.model import FitModelBase
from qudi.core.statusvariable import StatusVar


_log = logging.getLogger(__name__)


def is_fit_model(cls):
    return (
        inspect.isclass(cls)
        and issubclass(cls, FitModelBase)
        and (cls is not FitModelBase)
    )

_fit_models = dict()
for mod_finder in iter_modules_recursive(
    _fit_models_ns.__path__, _fit_models_ns.__name__ + '.'
):
        _fit_models.update(
            {
                name: cls
                for name, cls in inspect.getmembers(
                    importlib.import_module(mod_finder.name), is_fit_model
                )
            }
        )
   
_fit_configs = StatusVar(name='fit_configs', default=None)

__default_fit_configs = (
        {'name'             : 'Gaussian Dip',
         'model'            : 'Gaussian',
         'estimator'        : 'Dip',
         'custom_parameters': None},

        {'name'             : 'Two Gaussian Dips',
         'model'            : 'DoubleGaussian',
         'estimator'        : 'Dips',
         'custom_parameters': None},

        {'name'             : 'Lorentzian Dip',
         'model'            : 'Lorentzian',
         'estimator'        : 'Dip',
         'custom_parameters': None},

        {'name'             : 'Two Lorentzian Dips',
         'model'            : 'DoubleLorentzian',
         'estimator'        : 'Dips',
         'custom_parameters': None},
    )


@_fit_configs.representer
def __repr_fit_configs(self, value):
        configs = self.fit_config_model.dump_configs()
        if len(configs) < 1:
            configs = None
        return configs

@_fit_configs.constructor
def __constr_fit_configs(self, value):
        if not value:
            return self.__default_fit_configs
        return value

print(_fit_configs)