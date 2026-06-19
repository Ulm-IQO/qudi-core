# -*- coding: utf-8 -*-
"""
This module contains color scales and definitions for qudi as well as a custom matplotlib style.

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

__all__ = ['ColorScale', 'ColorScaleRainbow', 'ColorScaleMagma', 'ColorScaleInferno',
           'ColorScalePlasma', 'ColorScaleViridis', 'QudiPalette', 'QudiPalettePale',
           'QudiMatplotlibStyle']

import numpy as np
import pyqtgraph as pg
from cycler import cycler
from typing import Union, Optional


_DEFAULT_LUT_SIZE: int = 2000


class ColorScale:
    """Custom color scale base class for use in Qudi. Accepts either an already constructed
    pyqtgraph.ColorMap instance or a matplotlib colormap key string, e.g. "inferno".
    """
    colormap: pg.ColorMap
    lut: np.ndarray

    def __init__(self, colormap: Union[str, pg.ColorMap], lut_size: Optional[int] = _DEFAULT_LUT_SIZE):
        if isinstance(colormap, pg.ColorMap):
            self.colormap = colormap
        else:
            self.colormap = pg.colormap.getFromMatplotlib(colormap)
        # get the LookUpTable (LUT), first two params should match the position scale extremes
        # passed to ColorMap().
        # Return an RGB(A) lookup table (ndarray). Insert starting and stopping value and the
        # number of points in the returned lookup table:
        self.lut = self.colormap.getLookupTable(0, 1, lut_size)


class ColorScaleRainbow(ColorScale):
    """Rainbow color scale from matplotlib

    Looks ok but is not preferable for a number of reasons:
        - brightness linearity,
        - visual banding,
        - red-green colorblindness problems
        - and more...

    See the matplotlib discussion about their default color scale for reference.
    """
    def __init__(self, lut_size: Optional[int] = _DEFAULT_LUT_SIZE):
        super().__init__(colormap='rainbow', lut_size=lut_size)


class ColorScaleMagma(ColorScale):
    """Magma color scale from matplotlib"""
    def __init__(self, lut_size: Optional[int] = _DEFAULT_LUT_SIZE):
        super().__init__(colormap='magma', lut_size=lut_size)


class ColorScaleInferno(ColorScale):
    """Inferno color scale from matplotlib"""
    def __init__(self, lut_size: Optional[int] = _DEFAULT_LUT_SIZE):
        super().__init__(colormap='inferno', lut_size=lut_size)


class ColorScalePlasma(ColorScale):
    """Plasma color scale from matplotlib"""
    def __init__(self, lut_size: Optional[int] = _DEFAULT_LUT_SIZE):
        super().__init__(colormap='plasma', lut_size=lut_size)


class ColorScaleViridis(ColorScale):
    """Viridis color scale from matplotlib"""
    def __init__(self, lut_size: Optional[int] = _DEFAULT_LUT_SIZE):
        super().__init__(colormap='viridis', lut_size=lut_size)


class QudiPalette:
    """Qudi saturated color palette."""

    blue = pg.mkColor(34, 23, 244)
    c1 = blue

    orange = pg.mkColor(255, 164, 14)
    c2 = orange

    magenta = pg.mkColor(255, 52, 135)
    c3 = magenta

    green = pg.mkColor(0, 139, 0)
    c4 = green

    cyan = pg.mkColor(23, 190, 207)
    c5 = cyan

    purple = pg.mkColor(133, 0, 133)
    c6 = purple


class QudiPalettePale:
    """Qudi desaturated color palette."""

    blue = pg.mkColor(102, 94, 252)
    c1 = blue

    orange = pg.mkColor(255, 175, 43)
    c2 = orange

    magenta = pg.mkColor(255, 81, 152)
    c3 = magenta

    green = pg.mkColor(0, 179, 0)
    c4 = green

    cyan = pg.mkColor(59, 217, 233)
    c5 = cyan

    purple = pg.mkColor(188, 0, 188)
    c6 = purple


class QudiMatplotlibStyle:
    """Matplotlib style definition for this 'qudi-look'."""

    __mpl_colors = ['#1f17f4', '#ffa40e', '#ff3487', '#008b00', '#17becf', '#850085']
    __mpl_markers = ['o', 's', '^', 'v', 'D', 'd']

    style = {
        'axes.prop_cycle'      : cycler('color', __mpl_colors) + cycler('marker', __mpl_markers),
        'axes.edgecolor'       : '0.3',
        'xtick.color'          : '0.3',
        'ytick.color'          : '0.3',
        'axes.labelcolor'      : 'black',
        'font.size'            : '14',
        'lines.linewidth'      : '2',
        'figure.figsize'       : '12, 6',
        'lines.markeredgewidth': '0',
        'lines.markersize'     : '5',
        'axes.spines.right'    : True,
        'axes.spines.top'      : True,
        'xtick.minor.visible'  : True,
        'ytick.minor.visible'  : True,
        'savefig.dpi'          : '180'
    }