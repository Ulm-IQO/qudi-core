# -*- coding: utf-8 -*-

"""
This file contains unit tests for all qudi fit routines for exponential decay models.

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

from qudi.util.fit_models.exp_decay import ExponentialDecay
import numpy as np
import pytest

SEED = 42
# SEED = None
rng = np.random.default_rng(SEED)
_fit_param_tolerance = 0.05  # 5% tolerance for each fit parameter


def stretched_exp_decay(x, offset, amplitude, decay, stretch):
    return offset + amplitude * np.exp(-((x / decay) ** stretch))

def generate_params():
    offset = (rng.random() - 0.5) * 2e2
    amplitude = rng.random() * 1e4
    window = rng.integers(1, 2e1)
    left = rng.random()
    points = rng.integers(100, 1001)
    x_values = np.linspace(left, left + window, points)
    min_decay = 1.5 * (x_values[1] - x_values[0])
    decay = min_decay + rng.random() * ((window / 2) - min_decay)
    stretch = 0.1 + rng.random() * 3.9
    noise_amp = max(amplitude / 10, rng.random() * amplitude)
    noise = rng.uniform(-1, 1, points) * noise_amp * 0

    return offset, amplitude, decay, stretch, noise, x_values


def test_exp_decay_odmr_logic():
 
    offset, amplitude, decay, stretch, noise, x_values = generate_params()

    stretch = 1.0

    y_values = noise + stretched_exp_decay(
        x_values,
        offset,
        amplitude,
        decay,
        stretch,
    )
    
    model = ExponentialDecay()
    estimator = "Decay"
    add_parameters = None

    # Assume these are None for now until I figure out where they come from

    # add_parameters = config.custom_parameters
    if estimator is None:
        parameters = model.make_params()
    else:
        parameters = model.estimators[estimator](y_values, x_values)
    if add_parameters is not None:
        for name, param in add_parameters.items():
            parameters[name] = param
    result = model.fit(y_values, parameters, x=x_values)

    parameters_ideal = {
        "amplitude": amplitude,
        "offset": offset,
        "decay": decay,
    }

    # What the heck are high res fits?
    # # Mutate lmfit.ModelResult object to include high-resolution result curve
    # high_res_x = np.linspace(
    #     self.x_values[0], self.x_values[-1], len(self.x_values) * 10
    # )
    # result.high_res_best_fit = (
    #     high_res_x,
    #     model.eval(**result.best_values, x=high_res_x),
    # )

    print(result.best_values["amplitude"] / amplitude)
    # Check if the fit parameters are within the expected range
    for param, ideal_val in parameters_ideal.items():
        delta = abs(ideal_val - result.best_values[param])
        tol = abs(ideal_val * _fit_param_tolerance) 
        msg = f'Exp. decay fit parameter "{param}" has delta {delta:.2f} (Limit: {tol:.2f})'

        assert delta <= tol, msg


# def test_stretched_exp_decay(self):
#     y_values = self.noise + self.stretched_exp_decay(
#         self.x_values,
#         self.offset,
#         self.amplitude,
#         self.decay,
#         self.stretch,
#     )

#     model = ExponentialDecay()
#     # Assume these are None for now until I figure out where they come from
#     estimator = None
#     add_parameters = None

#     # estimator = config.estimator
#     # add_parameters = config.custom_parameters
#     if estimator is None:
#         parameters = model.make_params()
#     else:
#         parameters = model.estimators[estimator](y_values, self.x_values)
#     if add_parameters is not None:
#         for name, param in add_parameters.items():
#             parameters[name] = param
#     result = model.fit(y_values, parameters, x=self.x_values)

#     # What the heck are high res fits?
#     # # Mutate lmfit.ModelResult object to include high-resolution result curve
#     # high_res_x = np.linspace(
#     #     self.x_values[0], self.x_values[-1], len(self.x_values) * 10
#     # )
#     # result.high_res_best_fit = (
#     #     high_res_x,
#     #     model.eval(**result.best_values, x=high_res_x),
#     # )

#     # Check if the fit parameters are within the expected range
#     for name, ideal_val in result.best_values.items():
#         diff = abs(ideal_val - result.best_values[name])
#         tolerance = abs(ideal_val * self._fit_param_tolerance)
#         msg = f'Exp. decay fit parameter "{name}" has relative error {tolerance * 100:.2f}% (Limit: {self._fit_param_tolerance * 100:.2f}%)'

#         assert diff <= tolerance, msg
