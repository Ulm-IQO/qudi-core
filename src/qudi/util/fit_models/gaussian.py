# -*- coding: utf-8 -*-

"""
This file contains models of Gaussian fitting routines for qudi based on the lmfit package.

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

__all__ = ('DoubleGaussian', 'Gaussian', 'Gaussian2D', 'TripleGaussian', 'multiple_gaussian')

import numpy as np
from qudi.util.fit_models.model import FitModelBase, estimator
from qudi.util.fit_models.helpers import correct_offset_histogram, smooth_data, sort_check_data
from qudi.util.fit_models.helpers import estimate_double_peaks, estimate_triple_peaks
from qudi.util.fit_models.linear import Linear


def multiple_gaussian(x, centers, sigmas, amplitudes):
    """ Mathematical definition of the sum of multiple gaussian functions without any bias.

    WARNING: Iterable parameters "centers", "sigmas", and "amplitudes" must have the same length.

    Parameters
    ----------
    x : float
        The independent variable to calculate gauss(x).
    centers : iterable
        Iterable containing center positions for all Gaussians.
    sigmas : iterable
        Iterable containing standard deviations (sigmas) for all Gaussians.
    amplitudes : iterable
        Iterable containing amplitudes for all Gaussians.

    Returns
    -------
    float
        The result given x for gauss(x).

    """
    assert len(centers) == len(sigmas) == len(amplitudes)
    return sum(amp * np.exp(-((x - c) ** 2) / (2 * sig ** 2)) for c, sig, amp in
               zip(centers, sigmas, amplitudes))


class Gaussian(FitModelBase):
    """
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('center', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('sigma', value=0., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, center, sigma, amplitude):
        return offset + multiple_gaussian(x, (center,), (sigma,), (amplitude,))

    @estimator('Peak')
    def estimate_peak(self, data, x):
        # Sort and compute baseline from raw ends
        data, x = sort_check_data(data, x)
        n_end    = max(2, len(data) // 20)
        baseline = np.min(np.r_[data[:n_end], data[-n_end:]])
        data_bc  = data - baseline

        # Smooth for peak & half-max detection
        filt      = max(1, round(len(x) / 20))
        smooth, _ = smooth_data(data_bc, filt)
        idx_peak  = int(np.argmax(smooth))
        center    = x[idx_peak]
        amplitude = smooth[idx_peak]
        half_max  = amplitude / 2

        # Find FWHM edges by walking outwards and interpolating
        def interp_edge(i, direction):
            if i + direction >= len(x)  or i + direction < 0 :
                return None
            while 0 <= i + direction < len(x)-1 and smooth[i] >= half_max:
                i += direction
            i0, i1 = (i, i + 1) if direction > 1 else (i - 1, i)

            x0, y0 = x[i0], smooth[i0]
            x1, y1 = x[i1], smooth[i1]
            return x0 + (half_max - y0) * (x1 - x0) / (y1 - y0) if y1 != y0 else x0

        left_edge  = interp_edge(idx_peak, -1)
        right_edge = interp_edge(idx_peak, +1)
        if left_edge and right_edge:
            fwhm       = right_edge - left_edge
        elif left_edge:
            fwhm = (center - left_edge) * 2
        elif right_edge:
            fwhm = (right_edge - center) *2
        else:
            fwhm = min(center - x[0], x[-1] - center) *2
        sigma      = fwhm / (2 * np.sqrt(2 * np.log(2)))

        # Build params with sensible bounds
        span      = x[-1] - x[0]
        dx        = float(np.min(np.diff(x))) if len(x) > 1 else span
        data_span = smooth.max() - smooth.min()

        estimate = self.make_params()
        estimate['amplitude'].set(value=amplitude, min=0, max=2 * amplitude)
        estimate['center'].set(value=center,
                              min=x[0] - span/2, max=x[-1] + span/2)
        estimate['sigma'].set(value=max(sigma, dx),
                             min=dx, max=span)
        estimate['offset'].set(value=baseline,
                              min=baseline - data_span,
                              max=baseline + data_span)
        return estimate



    @estimator('Dip')
    def estimate_dip(self, data, x):
        estimate = self.estimate_peak(-data, x)
        estimate['offset'].set(value=-estimate['offset'].value,
                               min=-estimate['offset'].max,
                               max=-estimate['offset'].min)
        estimate['amplitude'].set(value=-estimate['amplitude'].value,
                                  min=-estimate['amplitude'].max,
                                  max=-estimate['amplitude'].min)
        return estimate

    @estimator('Peak (no offset)')
    def estimate_peak_no_offset(self, data, x):
        estimate = self.estimate_peak(data, x)
        estimate['offset'].set(value=0, min=-np.inf, max=np.inf, vary=False)
        return estimate

    @estimator('Dip (no offset)')
    def estimate_dip_no_offset(self, data, x):
        estimate = self.estimate_dip(data, x)
        estimate['offset'].set(value=0, min=-np.inf, max=np.inf, vary=False)
        return estimate


class DoubleGaussian(FitModelBase):
    """ ToDo: Document
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude_1', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude_2', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('center_1', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('center_2', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('sigma_1', value=0., min=0., max=np.inf)
        self.set_param_hint('sigma_2', value=0., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, center_1, center_2, sigma_1, sigma_2, amplitude_1, amplitude_2):
        return offset + multiple_gaussian(x,
                                          (center_1, center_2),
                                          (sigma_1, sigma_2),
                                          (amplitude_1, amplitude_2))

    @estimator('Peaks')
    def estimate_peaks(self, data, x):
        data, x = sort_check_data(data, x)
        data_smoothed, filter_width = smooth_data(data)
        leveled_data_smooth, offset = correct_offset_histogram(data_smoothed,
                                                               bin_width=2 * filter_width)
        estimate, limits = estimate_double_peaks(leveled_data_smooth, x, filter_width)

        params = self.make_params()
        params['amplitude_1'].set(value=estimate['height'][0],
                                  min=limits['height'][0][0],
                                  max=limits['height'][0][1])
        params['amplitude_2'].set(value=estimate['height'][1],
                                  min=limits['height'][1][0],
                                  max=limits['height'][1][1])
        params['center_1'].set(value=estimate['center'][0],
                               min=limits['center'][0][0],
                               max=limits['center'][0][1])
        params['center_2'].set(value=estimate['center'][1],
                               min=limits['center'][1][0],
                               max=limits['center'][1][1])
        params['sigma_1'].set(value=estimate['fwhm'][0] / 2.3548,
                              min=limits['fwhm'][0][0] / 2.3548,
                              max=limits['fwhm'][0][1] / 2.3548)
        params['sigma_2'].set(value=estimate['fwhm'][1] / 2.3548,
                              min=limits['fwhm'][1][0] / 2.3548,
                              max=limits['fwhm'][1][1] / 2.3548)
        return params

    @estimator('Dips')
    def estimate_dips(self, data, x):
        estimate = self.estimate_peaks(-data, x)
        estimate['offset'].set(value=-estimate['offset'].value,
                               min=-estimate['offset'].max,
                               max=-estimate['offset'].min)
        estimate['amplitude_1'].set(value=-estimate['amplitude_1'].value,
                                    min=-estimate['amplitude_1'].max,
                                    max=-estimate['amplitude_1'].min)
        estimate['amplitude_2'].set(value=-estimate['amplitude_2'].value,
                                    min=-estimate['amplitude_2'].max,
                                    max=-estimate['amplitude_2'].min)
        return estimate


class TripleGaussian(FitModelBase):
    """ ToDo: Document
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude_1', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude_2', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude_3', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('center_1', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('center_2', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('center_3', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('sigma_1', value=0., min=0., max=np.inf)
        self.set_param_hint('sigma_2', value=0., min=0., max=np.inf)
        self.set_param_hint('sigma_3', value=0., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, center_1, center_2, center_3, sigma_1, sigma_2, sigma_3,
                        amplitude_1, amplitude_2, amplitude_3):
        return offset + multiple_gaussian(x,
                                          (center_1, center_2, center_3),
                                          (sigma_1, sigma_2, sigma_3),
                                          (amplitude_1, amplitude_2, amplitude_3))

    @estimator('Peaks')
    def estimate_peaks(self, data, x):
        data, x = sort_check_data(data, x)
        data_smoothed, filter_width = smooth_data(data)
        leveled_data_smooth, offset = correct_offset_histogram(data_smoothed,
                                                               bin_width=2 * filter_width)
        estimate, limits = estimate_triple_peaks(leveled_data_smooth, x, filter_width)

        params = self.make_params()
        params['amplitude_1'].set(value=estimate['height'][0],
                                  min=limits['height'][0][0],
                                  max=limits['height'][0][1])
        params['amplitude_2'].set(value=estimate['height'][1],
                                  min=limits['height'][1][0],
                                  max=limits['height'][1][1])
        params['amplitude_3'].set(value=estimate['height'][2],
                                  min=limits['height'][2][0],
                                  max=limits['height'][2][1])
        params['center_1'].set(value=estimate['center'][0],
                               min=limits['center'][0][0],
                               max=limits['center'][0][1])
        params['center_2'].set(value=estimate['center'][1],
                               min=limits['center'][1][0],
                               max=limits['center'][1][1])
        params['center_3'].set(value=estimate['center'][2],
                               min=limits['center'][2][0],
                               max=limits['center'][2][1])
        params['sigma_1'].set(value=estimate['fwhm'][0] / 2.3548,
                              min=limits['fwhm'][0][0] / 2.3548,
                              max=limits['fwhm'][0][1] / 2.3548)
        params['sigma_2'].set(value=estimate['fwhm'][1] / 2.3548,
                              min=limits['fwhm'][1][0] / 2.3548,
                              max=limits['fwhm'][1][1] / 2.3548)
        params['sigma_3'].set(value=estimate['fwhm'][2] / 2.3548,
                              min=limits['fwhm'][2][0] / 2.3548,
                              max=limits['fwhm'][2][1] / 2.3548)
        return params

    @estimator('Dips')
    def estimate_dips(self, data, x):
        estimate = self.estimate_peaks(-data, x)
        estimate['offset'].set(value=-estimate['offset'].value,
                               min=-estimate['offset'].max,
                               max=-estimate['offset'].min)
        estimate['amplitude_1'].set(value=-estimate['amplitude_1'].value,
                                    min=-estimate['amplitude_1'].max,
                                    max=-estimate['amplitude_1'].min)
        estimate['amplitude_2'].set(value=-estimate['amplitude_2'].value,
                                    min=-estimate['amplitude_2'].max,
                                    max=-estimate['amplitude_2'].min)
        estimate['amplitude_3'].set(value=-estimate['amplitude_3'].value,
                                    min=-estimate['amplitude_3'].max,
                                    max=-estimate['amplitude_3'].min)
        return estimate


class GaussianLinear(FitModelBase):
    """
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('slope', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('center', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('sigma', value=0., min=0., max=np.inf)

    @staticmethod
    def _model_function(x, offset, slope, center, sigma, amplitude):
        x0 = (x - min(x))
        return offset + x0 * slope + multiple_gaussian(x, (center,), (sigma,), (amplitude,))

    @estimator('Peak')
    def estimate_peak(self, data, x):
        data, x = sort_check_data(data, x)
        data_span = abs(max(data) - min(data))

        # Perform a normal Gaussian peak fit and subtract the result from data
        model = Gaussian()
        gauss_fit = model.fit(data, model.estimate_peak(data, x), x=x)
        data_sub = data - gauss_fit.best_fit
        # Perform a linear fit in subtracted data in order to estimate slope
        model = Linear()
        linear_fit = model.fit(data_sub, model.estimate(data_sub, x), x=x)
        offset = linear_fit['offset'] + min(x) * linear_fit['slope']

        # Merge fit results into parameter estimates
        estimate = self.make_params()
        estimate['offset'].set(value=offset,
                               min=min(data) - data_span / 2,
                               max=max(data) + data_span / 2,
                               vary=True)
        estimate['slope'].set(value=linear_fit['slope'].value, min=-np.inf, max=np.inf, vary=True)
        estimate['amplitude'].set(value=gauss_fit['amplitude'].value,
                                  min=gauss_fit['amplitude'].min,
                                  max=gauss_fit['amplitude'].max,
                                  vary=True)
        estimate['center'].set(value=gauss_fit['center'].value,
                               min=gauss_fit['center'].min,
                               max=gauss_fit['center'].max,
                               vary=True)
        estimate['sigma'].set(value=gauss_fit['sigma'].value,
                              min=gauss_fit['sigma'].min,
                              max=gauss_fit['sigma'].max,
                              vary=True)
        return estimate

    @estimator('Dip')
    def estimate_dip(self, data, x):
        estimate = self.estimate_peak(-data, x)
        estimate['offset'].set(value=-estimate['offset'].value,
                               min=-estimate['offset'].max,
                               max=-estimate['offset'].min)
        estimate['amplitude'].set(value=-estimate['amplitude'].value,
                                  min=-estimate['amplitude'].max,
                                  max=-estimate['amplitude'].min)
        return estimate


class Gaussian2D(FitModelBase):
    """
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0, min=-np.inf, max=np.inf)
        self.set_param_hint('amplitude', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('center_x', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('center_y', value=0., min=-np.inf, max=np.inf)
        self.set_param_hint('sigma_x', value=0, min=0, max=np.inf)
        self.set_param_hint('sigma_y', value=0, min=0, max=np.inf)
        self.set_param_hint('theta', value=0., min=-np.pi, max=np.pi)

    @staticmethod
    def _model_function(x, offset, amplitude, center_x, center_y, sigma_x, sigma_y, theta):
        try:
            a = np.cos(-theta) ** 2 / (2 * sigma_x ** 2) + np.sin(-theta) ** 2 / (2 * sigma_y ** 2)
            b = np.sin(2 * -theta) / (4 * sigma_y ** 2) - np.sin(2 * -theta) / (4 * sigma_x ** 2)
            c = np.sin(-theta) ** 2 / (2 * sigma_x ** 2) + np.cos(-theta) ** 2 / (2 * sigma_y ** 2)
        except ZeroDivisionError:
            return np.full(x[0].shape, offset)
        x_prime = x[0] - center_x
        y_prime = x[1] - center_y
        gauss = offset + amplitude * np.exp(
            -(a * x_prime ** 2 + 2 * b * x_prime * y_prime + c * y_prime ** 2))
        return gauss.ravel()

    @estimator('Peak')
    def estimate_peak(self, data, x):
        # ToDo: Not properly implemented, yet
        x_range = abs(np.max(x[0]) - np.min(x[0]))
        y_range = abs(np.max(x[1]) - np.min(x[1]))

        amplitude = np.max(data)
        center_x = x_range / 2 + np.min(x[0])
        center_y = y_range / 2 + np.min(x[1])
        sigma_x = x_range / 10
        sigma_y = y_range / 10
        theta = 0

        estimate = self.make_params()
        estimate['offset'].set(value=np.mean(data), min=-np.inf, max=np.max(data))
        estimate['amplitude'].set(value=amplitude, min=0, max=amplitude * 2)
        estimate['center_x'].set(value=center_x,
                                 min=np.min(x[0]) - x_range / 2,
                                 max=np.max(x[0]) + x_range / 2)
        estimate['center_y'].set(value=center_y,
                                 min=np.min(x[1]) - y_range / 2,
                                 max=np.max(x[1]) + y_range / 2)
        estimate['sigma_x'].set(value=sigma_x, min=x_range / (x[0].shape[0] - 1), max=x_range)
        estimate['sigma_y'].set(value=sigma_y, min=y_range / (x[0].shape[1] - 1), max=y_range)
        estimate['theta'].set(value=theta, min=-np.pi, max=np.pi)
        return estimate

    @estimator('Dip')
    def estimate_dip(self, data, x):
        estimate = self.estimate_peak(-data, x)
        estimate['offset'].set(value=-estimate['offset'].value,
                               min=-estimate['offset'].max,
                               max=-estimate['offset'].min)
        estimate['amplitude'].set(value=-estimate['amplitude'].value,
                                  min=-estimate['amplitude'].max,
                                  max=-estimate['amplitude'].min)
        return estimate
