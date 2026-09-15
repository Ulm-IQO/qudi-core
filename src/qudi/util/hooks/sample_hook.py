from __future__ import annotations
import numpy as np
from qudi.util.hook import Hook

# Sample hook class for numpy ndarray to pass it as is
class NdarrayHook(Hook):
    target = np.ndarray
    def unstructure(self, obj):
        return obj
    def structure(self, value, type_):
        return value

