# -*- coding: utf-8 -*-
"""
This file contains qudi methods for mathematical operations/transformations.

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

__all__ = ('compute_ft', 'ft_windows')

import numpy as np
from scipy import signal

# Available windows to be applied on signal data before FT.
# To find out the amplitude normalization factor check either the scipy implementation on
#     https://github.com/scipy/scipy/blob/v0.15.1/scipy/signal/windows.py#L336
# or just perform a sum of the window (oscillating parts of the window should be averaged out and
# constant offset factor will remain):
#     MM=1000000  # choose a big number
#     print(sum(signal.hanning(MM))/MM)
ft_windows = {'none': {'func': np.ones, 'ampl_norm': 1.0},
              'hamming': {'func': signal.hamming, 'ampl_norm': 1.0/0.54},
              'hann': {'func': signal.hann, 'ampl_norm': 1.0/0.5},
              'blackman': {'func': signal.blackman, 'ampl_norm': 1.0/0.42},
              'triang': {'func': signal.triang, 'ampl_norm': 1.0/0.5},
              'flattop': {'func': signal.flattop, 'ampl_norm': 1.0/0.2156},
              'bartlett': {'func': signal.bartlett, 'ampl_norm': 1.0/0.5},
              'parzen': {'func': signal.parzen, 'ampl_norm': 1.0/0.375},
              'bohman': {'func': signal.bohman, 'ampl_norm': 1.0/0.4052847},
              'blackmanharris': {'func': signal.blackmanharris, 'ampl_norm': 1.0/0.35875},
              'nuttall': {'func': signal.nuttall, 'ampl_norm': 1.0/0.3635819},
              'barthann': {'func': signal.barthann, 'ampl_norm': 1.0/0.5}
              }


def compute_ft(x_val, y_val, zeropad_num=0, window='none', base_corr=True, psd=False):
    """Compute the Discrete fourier Transform of the power spectral density

    @param numpy.array x_val: 1D array
    @param numpy.array y_val: 1D array of same size as x_val
    @param int zeropad_num: optional, zeropadding (adding zeros to the end of the array).
                            zeropad_num >= 0, the size of the array which is add to the end of the
                            y_val before performing the Fourier Transform (FT). The resulting array
                            will have the length (len(y_val)/2)*(zeropad_num+1)
                            Note that zeropadding will not change or add more information to the
                            dft, it will solely interpolate between the dft_y values (corresponds
                            to a Sinc interpolation method).
                            Set zeropad_num=1 to obtain output arrays which have the same size as
                            the input arrays. Default is zeropad_num=0.
    @param str window: optional, the window function which should be applied to the y values before
                       Fourier Transform is calculated.
    @param bool base_corr: optional, select whether baseline correction shoud be performed before
                           calculating the FT. Default is False.
    @param bool psd: optional, select whether the Discrete Fourier Transform or the Power Spectral
                     Density (PSD, which is just the FT of the absolute square of the y-values)
                     should be computed. Default is psd=False.

    @return: tuple(dft_x, dft_y): be aware that the return arrays' length depend on the zeropad_num
                                  like len(dft_x) = len(dft_y) = (len(y_val)/2)*(zeropad_num+1)

    Pay attention that the return values of the FT have only half of the entries compared to the
    used signal input (if zeropad=0).

    In general, a window function should be applied on the y data before calculating the FT, to
    reduce spectral leakage. The Hann window for instance is almost never a bad choice. Use it like
    window='hann'

    Keep always in mind the relation to the Fourier transform space:
        T = delta_t * N_samples
    where delta_t is the distance between the time points and N_samples are the amount of points in
    the time domain. Consequently the sample rate is:
        f_samplerate = T / N_samples

    Keep also in mind that the FT returns value from 0 to f_samplerate, or equivalently
    -f_samplerate/2 to f_samplerate/2.

    Difference between PSD and DFT:
    The power spectral density (PSD) describes how the power of your signal is distributed over
    frequency whilst the DFT shows the spectral content of your signal, i.e. the amplitude and
    phase of harmonics in your signal.
    """

    x_val = np.array(x_val)
    y_val = np.array(y_val)

    # Make a baseline correction to avoid a constant offset near zero frequencies. Offset of the
    # y_val from mean corresponds to half the value at fft_y[0]
    corrected_y = y_val
    if base_corr:
        corrected_y = y_val - y_val.mean()

    ampl_norm_fact = 1.0
    # apply window to data to account for spectral leakage:
    if window in ft_windows:
        window_val = ft_windows[window]['func'](len(y_val))
        corrected_y = corrected_y * window_val
        # to get the correct amplitude in the amplitude spectrum
        ampl_norm_fact = ft_windows[window]['ampl_norm']

    # zeropad for sinc interpolation:
    zeropad_arr = np.zeros(len(corrected_y)*(zeropad_num+1))
    zeropad_arr[:len(corrected_y)] = corrected_y

    # Get the amplitude values from the fourier transformed y values.
    fft_y = np.abs(np.fft.fft(zeropad_arr))

    # Power spectral density (PSD) or just amplitude spectrum of fourier signal:
    power_value = 1.0
    if psd:
        power_value = 2.0

    # The factor 2 accounts for the fact that just the half of the spectrum was taken. The
    # ampl_norm_fact is the normalization factor due to the applied window function (the offset
    # value in the window function):
    fft_y = ((2/len(y_val)) * fft_y * ampl_norm_fact)**power_value

    # Due to the sampling theorem you can only identify frequencies at half of the sample rate,
    # therefore the FT contains an almost symmetric spectrum (the asymmetry results from aliasing
    # effects). Therefore take the half of the values for the display.
    middle = int((len(zeropad_arr)+1)//2)

    # sample spacing of x_axis, if x is a time axis than it corresponds to a timestep:
    x_spacing = np.round(x_val[-1] - x_val[-2], 12)

    # use the helper function of numpy to calculate the x_values for the fourier space. That
    # function will handle an occuring devision by 0:
    fft_x = np.fft.fftfreq(len(zeropad_arr), d=x_spacing)
    return abs(fft_x[:middle]), fft_y[:middle]

def normalize(arr:np.ndarray, axis=-1, order=2)->np.ndarray:
    """
    Taken from stack overflow
    https://stackoverflow.com/questions/21030391/how-to-normalize-a-numpy-array-to-a-unit-vector
    """
    l2 = np.atleast_1d(np.linalg.norm(arr, order, axis))
    l2[l2==0] = 1
    return arr / np.expand_dims(l2, axis)

