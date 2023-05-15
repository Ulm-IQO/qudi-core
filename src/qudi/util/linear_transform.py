# -*- coding: utf-8 -*-
"""
This module provides functionality for linear transformations of cartesian coordinate systems.

Copyright (c) 2022, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-iqo-modules/>

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

__all__ = ['LinearTransformation', 'LinearTransformation3D', 'LinearTransformation2D']

import numpy as np
from typing import Sequence, Optional, Union, Tuple

from qudi.util.helpers import is_integer


class LinearTransformation:
    """ Linear transformation for N-dimensional cartesian coordinates """

    def __init__(self,
                 matrix: Optional[Sequence[Sequence[float]]] = None,
                 dimensions: Optional[int] = None
                 ) -> None:
        super().__init__()

        if matrix is not None:
            self._matrix = np.array(matrix, dtype=float)
            if self._matrix.ndim != 2:
                raise ValueError('LinearTransformation matrix must be 2-dimensional')
            if self._matrix.shape[0] != self._matrix.shape[1]:
                raise ValueError('LinearTransformation matrix must be square')
        elif dimensions is not None:
            if not is_integer(dimensions):
                raise TypeError(f'LinearTransformation dimensions must be integer type. '
                                f'Received {type(dimensions)} instead.')
            if dimensions < 1:
                raise ValueError(f'LinearTransformation dimensions must >= 1. '
                                 f'Received {dimensions:d} instead.')
            self._matrix = np.eye(dimensions + 1, dimensions + 1)
        else:
            raise ValueError('Must either provide homogenous transformation matrix or number of '
                             'dimensions')

    def __call__(self,
                 nodes: Union[Sequence[float], Sequence[Sequence[float]]],
                 invert: Optional[bool] = False
                 ) -> np.ndarray:
        """ Transforms any single node (vector) or sequence of nodes according to the
        preconfigured matrix.
        Tries to perform the inverse transform if the optional argument invert is True.
        """
        nodes = np.squeeze(np.asarray(nodes))
        node_dim = np.ndim(nodes)
        matrix = self.inverse if invert else self._matrix
        if node_dim == 2:
            nodes = np.vstack([nodes.T, np.full(nodes.shape[0], 1)])
            return np.matmul(matrix, nodes)[:self.dimensions, :].T
        elif node_dim == 1:
            nodes = np.append(nodes, 1)
            return np.matmul(matrix, nodes)[:self.dimensions]
        raise ValueError('nodes to transform must either be 1D or 2D array')

    @property
    def matrix(self) -> np.ndarray:
        """ Returns a copy of the currently configured homogenous transformation matrix
        (including translation)
        """
        return self._matrix.copy()

    @property
    def inverse(self) -> np.ndarray:
        """ Returns a copy of the inverse of the currently configured homogenous transformation
        matrix
        """
        return np.linalg.inv(self._matrix)

    @property
    def dimensions(self) -> int:
        """ Returns the number of dimensions of the coordinate system to transform.
        The homogenous transformation matrix is a square matrix with (dimensions + 1) rows/columns
        """
        return self._matrix.shape[0] - 1

    def add_transform(self, matrix: Sequence[Sequence[float]]) -> None:
        """ Multiply a given homogenous transformation matrix (including translation) onto the
        current trasnformation matrix.
        """
        matrix = np.asarray(matrix, dtype=float)
        if matrix.shape != self._matrix.shape:
            raise ValueError(f'LinearTransformation.add_transform expects a homogenious '
                             f'transformation matrix with the same shape as '
                             f'LinearTransformation.matrix {self._matrix.shape}. '
                             f'Received {matrix.shape} instead.')
        self._matrix = np.matmul(matrix, self._matrix)

    def translate(self, *args: float) -> None:
        """ Adds a translation to the transformation. Must provide a displacement argument for
        each dimension.
        """
        dim = self.dimensions
        if len(args) != dim:
            raise ValueError(f'LinearTransformation.translate requires as many arguments as '
                             f'number of dimensions ({dim:d})')
        translate_matrix = np.zeros(self._matrix.shape, dtype=float)
        translate_matrix[-1, -1] = 1
        translate_matrix[:-1, -1] = args
        self.add_transform(translate_matrix)

    def scale(self, *args: float) -> None:
        """ Adds scaling to the transformation. Must provide a scale factor argument for each
        dimension.
        """
        diagonal = np.ones(self._matrix.shape[0], dtype=float)
        if len(args) == 1:
            diagonal[:-1] *= args[0]
        elif len(args) == self.dimensions:
            diagonal[:-1] *= args
        else:
            raise ValueError(f'LinearTransformation.scale requires either a single argument or as '
                             f'many arguments as number of dimensions ({self.dimensions:d})')
        scale_matrix = np.diag(diagonal)
        self.add_transform(scale_matrix)

    def rotate(self, *args, **kwargs) -> None:
        """ Adds a rotation to the transformation. Must provide a rotation angle argument for each
        axis (dimension).
        """
        raise NotImplementedError('Arbitrary rotation transformation not implemented yet')

    def from_support_vectors(self):
        # todo
        pass

class LinearTransformation3D(LinearTransformation):
    """ Linear transformation for 3D cartesian coordinates """

    _Vector = Tuple[float, float, float, float]
    _TransformationMatrix = Tuple[_Vector, _Vector, _Vector, _Vector]

    def __init__(self, matrix: Optional[_TransformationMatrix] = None) -> None:
        super().__init__(matrix=matrix, dimensions=3)

    def rotate(self,
               x_angle: Optional[float] = 0,
               y_angle: Optional[float] = 0,
               z_angle: Optional[float] = 0
               ) -> None:
        """ Adds a rotation to the transformation. Can provide a rotation angle (in rad) around
        each of the 3 axes (x, y, z).
        """
        sin_a = np.sin(x_angle)
        cos_a = np.cos(x_angle)
        sin_b = np.sin(y_angle)
        cos_b = np.cos(y_angle)
        sin_c = np.sin(z_angle)
        cos_c = np.cos(z_angle)
        rot_matrix = np.array([
            [cos_b * cos_c, sin_a * sin_b * cos_c - cos_a * sin_c, cos_a * sin_b * cos_c + sin_a * sin_c, 0],
            [cos_b * sin_c, sin_a * sin_b * sin_c + cos_a * cos_c, cos_a * sin_b * sin_c - sin_a * cos_c, 0],
            [-sin_b,        sin_a * cos_b,                         cos_a * cos_b,                         0],
            [0,             0,                                     0,                                     1]
        ])
        self.add_transform(rot_matrix)

    def translate(self,
                  dx: Optional[float] = 0,
                  dy: Optional[float] = 0,
                  dz: Optional[float] = 0
                  ) -> None:
        """ Adds a translation to the transformation. Can provide a displacement for each of the 3
        axes (x, y, z).
        """
        return super().translate(dx, dy, dz)

    def scale(self,
              sx: Optional[float] = 1,
              sy: Optional[float] = 1,
              sz: Optional[float] = 1
              ) -> None:
        """ Adds scaling to the transformation. Can provide a scale factor for each of the 3 axes
        (x, y, z).
        """
        return super().scale(sx, sy, sz)

    def add_rotation(self, matrix) -> None:
        """
        Add a rotation given by 3x3 matrix. Pad the array to represent this rotation plus a zero translation.
        :param matrix:
        :return:
        """
        rot_matrix = np.pad(matrix, [(0, 1), (0, 1)])
        rot_matrix[-1,-1] = 1

        self.add_transform(rot_matrix)


class LinearTransformation2D(LinearTransformation):
    """ Linear transformation for 2D cartesian coordinates """

    _Vector = Tuple[float, float, float]
    _TransformationMatrix = Tuple[_Vector, _Vector, _Vector]

    def __init__(self, matrix: Optional[_TransformationMatrix] = None) -> None:
        super().__init__(matrix=matrix, dimensions=2)

    def rotate(self, angle: float) -> None:
        """ Adds a rotation to the transformation. Given angle (in rad) will rotate around origin
        counter-clockwise.
        """
        cos = np.cos(angle)
        sin = np.sin(angle)
        rot_matrix = np.array([
            [cos, -sin, 0],
            [sin,  cos, 0],
            [0  ,    0, 1]
        ])
        self.add_transform(rot_matrix)

    def translate(self, dx: Optional[float] = 0, dy: Optional[float] = 0) -> None:
        """ Adds a translation to the transformation. Can provide a displacement for each of the 2
        axes (x, y).
        """
        return super().translate(dx, dy)

    def scale(self, sx: Optional[float] = 1, sy: Optional[float] = 1) -> None:
        """ Adds scaling to the transformation. Can provide a scale factor for each of the 2 axes
        (x, y).
        """
        return super().scale(sx, sy)
