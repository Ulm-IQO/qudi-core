# -*- coding: utf-8 -*-
"""
This module is provides functionality to transform coordinate systems.

Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
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
from typing import Sequence, Optional, Union

from qudi.util.helpers import is_integer


class LinearTransformation:
    """ """

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

    def __call__(self, nodes: Union[Sequence[float], Sequence[Sequence[float]]]) -> np.ndarray:
        nodes = np.squeeze(np.asarray(nodes))
        node_dim = np.ndim(nodes)
        if node_dim == 2:
            nodes = np.vstack([nodes.T, np.full(nodes.shape[0], 1)])
            return np.matmul(self._matrix, nodes)[:self.dimensions, :].T
        elif node_dim == 1:
            nodes = np.append(nodes, 1)
            return np.matmul(self._matrix, nodes)[:self.dimensions]
        raise ValueError('nodes to transform must either be 1D or 2D array')

    @property
    def matrix(self) -> np.ndarray:
        return self._matrix.copy()

    @property
    def inverse(self) -> np.ndarray:
        return np.linalg.inv(self._matrix)

    @property
    def dimensions(self) -> int:
        return self._matrix.shape[0] - 1

    def translate(self, *args: float) -> None:
        dim = self.dimensions
        if len(args) != dim:
            raise ValueError(f'LinearTransformation.translate requires as many arguments as '
                             f'number of dimensions ({dim:d})')
        self._matrix[:dim, dim] += args

    def scale(self, *args: float) -> None:
        dim = self.dimensions
        if len(args) == 1:
            scale_matrix = np.eye(dim) * args[0]
        elif len(args) == dim:
            scale_matrix = np.diag(args)
        else:
            raise ValueError(f'LinearTransformation.scale requires either a single argument or as '
                             f'many arguments as number of dimensions ({dim:d})')
        self._matrix[:dim, :dim] *= scale_matrix

    def rotate(self, *args, **kwargs) -> None:
        raise NotImplementedError('Arbitrary rotation transformation not implemented yet')


class LinearTransformation3D(LinearTransformation):
    """
    """
    def __init__(self, matrix: Optional[Sequence[Sequence[float]]] = None) -> None:
        super().__init__(matrix=matrix, dimensions=3)

    def rotate(self, alpha: float, beta: float, gamma: float) -> None:
        sin_a = np.sin(alpha)
        cos_a = np.cos(alpha)
        sin_b = np.sin(beta)
        cos_b = np.cos(beta)
        sin_c = np.sin(gamma)
        cos_c = np.cos(gamma)
        rot = np.array([
            [cos_b * cos_c, sin_a * sin_b * cos_c - cos_a * sin_c, cos_a * sin_b * cos_c + sin_a * sin_c],
            [cos_b * sin_c, sin_a * sin_b * sin_c + cos_a * cos_c, cos_a * sin_b * sin_c - sin_a * cos_c],
            [-sin_b, sin_a * cos_b, cos_a * cos_b]
        ])
        self._matrix[:3, :3] = np.matmul(rot, self._matrix[:3, :3])

    def translate(self,
                  dx: Optional[float] = 0,
                  dy: Optional[float] = 0,
                  dz: Optional[float] = 0
                  ) -> None:
        return super().translate(dx, dy, dz)

    def scale(self,
              sx: Optional[float] = 1,
              sy: Optional[float] = 1,
              sz: Optional[float] = 1
              ) -> None:
        return super().scale(sx, sy, sz)


class LinearTransformation2D(LinearTransformation):
    """
    """
    def __init__(self, matrix: Optional[Sequence[Sequence[float]]] = None) -> None:
        super().__init__(matrix=matrix, dimensions=2)

    def rotate(self, angle: float) -> None:
        cos = np.cos(angle)
        sin = np.sin(angle)
        rot = np.array([
            [cos,  -sin],
            [sin, cos]
        ])
        self._matrix[:2, :2] = np.matmul(rot, self._matrix[:2, :2])

    def translate(self, dx: Optional[float] = 0, dy: Optional[float] = 0) -> None:
        return super().translate(dx, dy)

    def scale(self, sx: Optional[float] = 1, sy: Optional[float] = 1) -> None:
        return super().scale(sx, sy)
