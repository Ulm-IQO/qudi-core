# -*- coding: utf-8 -*-

"""
This file contains unit tests for all qudi fit routines for Lorentzian peak/dip models.

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

import unittest
import numpy as np

from qudi.util.fit_models.lorentzian import Lorentzian


class TestLorentzianMethods(unittest.TestCase):
    _fit_param_tolerance = 0.05  # 5% tolerance for each fit parameter

    @staticmethod
    def lorentzian(x, offset, amplitude, center, sigma):
        return offset + amplitude * sigma**2 / ((x - center) ** 2 + sigma**2)

    def setUp(self):
        self.offset = (np.random.rand() - 0.5) * 2e6
        self.amplitude = np.random.rand() * 100
        window = max(1e-9, np.random.rand() * 1e9)
        left = (np.random.rand() - 0.5) * 2e9
        points = np.random.randint(10, 1001)
        self.x_values = np.linspace(left, left + window, points)
        min_sigma = 1.5 * (self.x_values[1] - self.x_values[0])
        self.sigma = min_sigma + np.random.rand() * ((window / 2) - min_sigma)
        self.center = left + np.random.rand() * window
        self.noise_amp = max(self.amplitude / 10, np.random.rand() * self.amplitude)
        self.noise = (np.random.rand(points) - 0.5) * self.noise_amp

    def test_gaussian(self):
        # Test for lorentzian peak
        y_values = self.noise + self.lorentzian(
            self.x_values, self.offset, self.amplitude, self.center, self.sigma
        )

        fit_model = Lorentzian()
        fit_result = fit_model.fit(
            data=y_values, x=self.x_values, **fit_model.guess(y_values, self.x_values)
        )

        params_ideal = {
            'offset': self.offset,
            'amplitude': self.amplitude,
            'center': self.center,
            'sigma': self.sigma,
        }
        for name, fit_param in fit_result.best_values.items():
            diff = abs(fit_param - params_ideal[name])
            tolerance = abs(params_ideal[name] * self._fit_param_tolerance)
            msg = 'Lorentzian peak fit parameter "{0}" not within {1:.2%} tolerance'.format(
                name, self._fit_param_tolerance
            )
            self.assertLessEqual(diff, tolerance, msg)

        # Test for lorentzian dip
        y_values = self.noise + self.lorentzian(
            self.x_values, self.offset, -self.amplitude, self.center, self.sigma
        )

        fit_model = Lorentzian()
        fit_result = fit_model.fit(
            data=y_values, x=self.x_values, **fit_model.guess(y_values, self.x_values)
        )

        params_ideal['amplitude'] = -self.amplitude
        for name, fit_param in fit_result.best_values.items():
            diff = abs(fit_param - params_ideal[name])
            tolerance = abs(params_ideal[name] * self._fit_param_tolerance)
            msg = 'Lorentzian dip fit parameter "{0}" not within {1:.2%} tolerance'.format(
                name, self._fit_param_tolerance
            )
            self.assertLessEqual(diff, tolerance, msg)


if __name__ == '__main__':
    unittest.main()
