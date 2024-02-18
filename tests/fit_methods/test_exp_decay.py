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
NUM_TESTS = 10
NUM_X_VALUES = 1_000
RTOL = 0.05
ATOL = 1e-3
SMALL_VALUE_ATOL = 1e-5

rng = np.random.default_rng(seed=SEED)


@pytest.fixture
def generate_params():
    amplitude = rng.uniform(
        1e1, 1e3
    )  # If this is too small, the fit errors become large
    decay = rng.uniform(1, 10)
    x_values = np.linspace(0, 100, NUM_X_VALUES)
    noise = rng.normal(0, 0.1, x_values.shape)

    yield amplitude, decay, x_values, noise


@pytest.mark.parametrize("generate_params", range(NUM_TESTS), indirect=True)
@pytest.mark.parametrize("stretch", [1.0] + list(rng.uniform(0, 10, NUM_TESTS - 1)))
@pytest.mark.parametrize("offset", [0.0] + list(rng.uniform(1e2, 1e3, NUM_TESTS - 1)))
def test_exp_decay(generate_params, stretch, offset):
    amplitude, decay, x_values, noise = generate_params

    y_values = noise + ExponentialDecay().eval(
        x=x_values, offset=offset, amplitude=amplitude, decay=decay, stretch=stretch
    )

    fit_model = ExponentialDecay()
    if stretch == 1.0:
        if offset == 0.0:
            estimate = fit_model.estimate_decay_no_offset(y_values, x_values)
        else:
            estimate = fit_model.estimate_decay(y_values, x_values)
    else:
        if offset == 0.0:
            estimate = fit_model.estimate_stretched_decay_no_offset(y_values, x_values)
        else:
            estimate = fit_model.estimate_stretched_decay(y_values, x_values)

    fit_result = fit_model.fit(data=y_values, x=x_values, **estimate)

    params_ideal = {
        "offset": offset,
        "amplitude": amplitude,
        "decay": decay,
        "stretch": stretch,
    }
    for name, ideal_val in params_ideal.items():
        fit_val = fit_result.best_values[name]
        if ideal_val >= SMALL_VALUE_ATOL:
            relative_err = abs(abs(fit_val - ideal_val) / ideal_val)
            msg = f'Exp. decay fit parameter "{name}" has relative error {relative_err * 100:.2f}% (Limit: {RTOL * 100:.2f}%)'
            assert relative_err <= RTOL, msg
        else:
            absolute_err = abs(fit_val - ideal_val)
            msg = f'Exp. decay fit parameter "{name}" has absolute error {absolute_err:.5f}% (Limit: {ATOL * 100:.2f})'
            assert absolute_err <= ATOL, msg


if __name__ == "__main__":
    pytest.main()
