# -*- coding: utf-8 -*-

"""
This file contains modified pyqtgraph.ImageItem subclasses for data visualization.

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

__all__ = ['DataImageItem', 'XYPlotItem']

import numpy as np
from typing import Union, Optional, Tuple
from PySide2 import QtCore
from pyqtgraph import ImageItem as _ImageItem
from pyqtgraph import PlotDataItem as _PlotDataItem

from qudi.util.colordefs import ColorScaleInferno as _Colorscale
from qudi.util.colordefs import QudiPalette as _QudiPalette


class XYPlotItem(_PlotDataItem):
    """ Extension of pg.PlotDataItem with default qudi style plot options """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        self.opts['pen'] = _QudiPalette.c1
        self.opts['symbolPen'] = _QudiPalette.c1
        self.opts['symbolBrush'] = _QudiPalette.c1
        self.setData(*args, **kwargs)


class DataImageItem(_ImageItem):
    """ Extension of pg.ImageItem with percentile level scaling and image size adjustment """

    def __init__(self, image=None, **kwargs):
        # Change default color scale to qudi default
        if kwargs.get('lut', None) is None:
            kwargs['lut'] = _Colorscale().lut
        super().__init__(image, **kwargs)
        self._percentiles = None

    @property
    def percentiles(self) -> Union[None, Tuple[float, float]]:
        return self._percentiles

    def set_percentiles(self, percentiles: Union[None, Tuple[float, float]]) -> None:
        """ Set percentile range to clip image color level scaling.
        """
        if percentiles is not None:
            percentiles = (min(percentiles), max(percentiles))
        if percentiles != self._percentiles:
            self._percentiles = percentiles
            if self.image is not None:
                masked_image = np.ma.masked_invalid(self.image).compressed()
                if masked_image.size > 0:
                    self.setLevels(self._get_percentile_levels(masked_image))

    def set_image_extent(self,
                         extent: Tuple[Tuple[float, float], Tuple[float, float]],
                         adjust_for_px_size: Optional[bool] = True
                         ) -> None:
        """ Scales the image to a certain value range. By default, the resulting extent will be a
        bit larger, so that each pixel center corresponds to the respective xy coordinate.
        """
        if adjust_for_px_size is None:
            adjust_for_px_size = True
        if len(extent) != 2:
            raise ValueError('Image extent must be float sequence of length 2')
        if len(extent[0]) != 2 or len(extent[1]) != 2:
            raise TypeError('Image extent for each axis must be sequence of length 2.')

        if self.image is not None:
            x_min, x_max = min(extent[0]), max(extent[0])
            y_min, y_max = min(extent[1]), max(extent[1])
            if adjust_for_px_size:
                if self.image.shape[0] > 1 and self.image.shape[1] > 1:
                    half_px_x = (x_max - x_min) / (2 * (self.image.shape[0] - 1))
                    half_px_y = (y_max - y_min) / (2 * (self.image.shape[1] - 1))
                    x_min -= half_px_x
                    x_max += half_px_x
                    y_min -= half_px_y
                    y_max += half_px_y
            self.setRect(QtCore.QRectF(x_min, y_min, x_max - x_min, y_max - y_min))

    def set_image(self, image=None, **kwargs):
        """ vpg.ImageItem method override to apply optional filter when setting image data.
        """
        if image is None:
            self.clear()
        else:
            masked_image = np.ma.masked_invalid(image).compressed()
            if masked_image.size > 0:
                kwargs['levels'] = kwargs.get('levels', self._get_percentile_levels(masked_image))
                self.setImage(image=image, **kwargs)
            else:
                self.clear()

    def _get_percentile_levels(self, image) -> Tuple[float, float]:
        if self._percentiles is None:
            min_value = np.min(image)
            max_value = np.max(image)
        else:
            min_value = np.percentile(image, self._percentiles[0])
            max_value = np.percentile(image, self._percentiles[1])
        return min_value, max_value
