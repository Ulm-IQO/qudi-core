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

import pytest
import numpy as np

from qudi.util.fit_models.exp_decay import ExponentialDecay


SEED = 42
NUM_TESTS = 100
NUM_X_VALUES = 1000
TOLERANCE = 0.05

rng = np.random.default_rng(seed=SEED)


@pytest.fixture
def generate_params():
    offset = rng.uniform(1e2, 1e3)
    amplitude = rng.uniform(1e1, 1e3)  # If this is too small, the fit errors become large
    decay = rng.uniform(1, 10)
    stretch = rng.random()
    x_values = np.linspace(0, 100, NUM_X_VALUES)
    noise = rng.normal(0, 0.1, x_values.shape)

    yield offset, amplitude, decay, stretch, x_values, noise


@pytest.mark.parametrize("generate_params", range(NUM_TESTS), indirect=True)
def test_exp_decay(generate_params):
    offset, amplitude, decay, stretch, x_values, noise = generate_params

    stretch = 1
    y_values = noise + ExponentialDecay().eval(
        x=x_values, offset=offset, amplitude=amplitude, decay=decay, stretch=stretch
    )

    fit_model = ExponentialDecay()
    estimate = fit_model.guess(y_values, x_values)
    estimate["stretch"].set(vary=False, value=stretch)
    fit_result = fit_model.fit(data=y_values, x=x_values, **estimate)

    params_ideal = {
        "offset": offset,
        "amplitude": amplitude,
        "decay": decay,
        "stretch": stretch,
    }
    for name, ideal_val in params_ideal.items():
        fit_val = fit_result.best_values[name]
        relative_err = abs(abs(fit_val - ideal_val) / ideal_val)
        # msg = f'Exp. decay fit parameter "{name}" has relative error {relative_err * 100:.2f}% (Limit: {TOLERANCE * 100:.2f}%)'
        msg = f'Actual: {fit_val}, Ideal: {ideal_val}, {name}, Relative error: {relative_err * 100:.2f}%, Absolute error: {abs(fit_val - ideal_val)}'
        assert relative_err <= TOLERANCE, msg


if __name__ == "__main__":
    pytest.main()

# @pytest.mark.parametrize("stretch", [0.1 + rng.random() * 3.9])
# def test_stretched_exp_decay(setup_values, stretch):
#     offset, amplitude, decay, _, x_values, noise = setup_values

#     y_values = noise + (offset + amplitude * np.exp(-((x_values / decay) ** stretch)))

#     fit_model = ExponentialDecay()
#     fit_result = fit_model.fit(
#         data=y_values, x=x_values, **fit_model.guess(y_values, x_values)
#     )

#     params_ideal = {
#         "offset": offset,
#         "amplitude": amplitude,
#         "decay": decay,
#         "stretch": stretch,
#     }
#     for name, ideal_val in params_ideal.items():
#         diff = abs(fit_result.best_values[name] - ideal_val)
#         tolerance = abs(ideal_val * 0.05)
#         msg = 'Stretched exp. decay fit parameter "{0}" not within {1:.2%} tolerance'.format(
#             name, 0.05
#         )
#         assert diff <= tolerance
