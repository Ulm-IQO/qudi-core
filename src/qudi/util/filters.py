# -*- coding: utf-8 -*-
"""
This file contains Qudi methods for data filtering.

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

__all__ = ('scan_blink_correction',)

import numpy as np
from scipy.ndimage import minimum_filter1d, maximum_filter1d
import logging

_logger = logging.getLogger(__name__)


def scan_blink_correction(image, axis=1):
    """
    Filter out impulsive noise from a 2D array along a single axis using an opening filter.

    The opening filter applies a sequence of two filters: first a min-filter and then a max-filter.
    This technique is effective at removing single-pixel brightness spikes along the specified axis,
    but it may make the image appear more "blocky" or less smooth.

    Parameters
    ----------
    image : numpy.ndarray
        A 2D numpy array to be filtered (e.g., image data).
    axis : int
        The axis along which to apply the 1D filter.

    Returns
    -------
    numpy.ndarray
        The filtered image, with the same dimensions as the input image.

    Notes
    -----
    Ensure that the image features of interest are larger than the impulsive noise spikes
    to achieve effective noise reduction without loss of significant image detail.

    """

    if not isinstance(image, np.ndarray):
        _logger.error('Image must be 2D numpy array.')
        return image
    if image.ndim != 2:
        _logger.error('Image must be 2D numpy array.')
        return image
    if axis != 0 and axis != 1:
        _logger.error('Optional axis parameter must be either 0 or 1.')
        return image

    # Calculate median value of the image. This value is used for padding image boundaries during
    # filtering.
    median = np.median(image)
    # Apply a minimum filter along the chosen axis.
    filt_img = minimum_filter1d(image, size=2, axis=axis, mode='constant', cval=median)
    # Apply a maximum filter along the chosen axis. Flip the previous filter result to avoid
    # translation of image features.
    filt_img = maximum_filter1d(
        np.flip(filt_img, axis), size=2, axis=axis, mode='constant', cval=median
    )
    # Flip back the image to obtain original orientation and return result.
    return np.flip(filt_img, axis)
