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
fit_param_rel_tol = 0.05  # 5% tolerance for each fit parameter
NUM_TESTS = 10

estimators = ExponentialDecay().estimators.keys()


def stretched_exp_decay(x, offset, amplitude, decay, stretch):
    return offset + amplitude * np.exp(-((x / decay) ** stretch))


@pytest.fixture
def generate_params():
    amplitude = 1e3 + rng.random() * 1e4

    offset = amplitude * rng.uniform(0.05, 0.1)

    window = rng.integers(1e1, 1e3)
    points = np.round(window * rng.uniform(1, 10)).astype(int)
    x_values = np.linspace(0, window, points)

    min_decay = (x_values[1] - x_values[0]) * window
    decay = min_decay * rng.uniform(0, 2)  # smaller means faster decay
    # decay = min_decay * rng.uniform(1, 2)

    stretch = 1 + rng.random()

    noise_std = 0.01
    noise = rng.normal(1, noise_std, points)

    yield offset, amplitude, decay, stretch, noise, x_values


@pytest.mark.parametrize(
    'generate_params', [generate_params for _ in range(NUM_TESTS)], indirect=True
)
@pytest.mark.parametrize('estimator', estimators)
def test_exp_decay(generate_params, estimator):
    offset, amplitude, decay, stretch, noise, x_values = generate_params

    if estimator == 'Decay':
        stretch = 1.0
    elif estimator == 'Decay (no offset)':
        stretch = 1.0
        offset = 0.0
    elif estimator == 'Stretched Decay (no offset)':
        offset = 0.0
    elif estimator == 'Stretched Decay':
        pass
    else:
        raise ValueError(f'Unknown estimator: {estimator}')

    parameters_ideal = {
        'amplitude': amplitude,
        'offset': offset,
        'decay': decay,
        'stretch': stretch,
    }

    y_values = noise * stretched_exp_decay(
        x_values,
        offset,
        amplitude,
        decay,
        stretch,
    )

    model = ExponentialDecay()
    parameters = model.estimators[estimator](y_values, x_values)

    result = model.fit(y_values, parameters, x=x_values)

    # Check if the fit parameters are within the expected range
    for param, ideal_val in parameters_ideal.items():
        try:
            rel_err = abs(abs(ideal_val - result.best_values[param]) / ideal_val)
            msg = f'Exp. decay fit parameter "{param}" has relative error {rel_err * 100 :.2f}% (Limit: {fit_param_rel_tol * 100:.2f}%)'

        except ZeroDivisionError:
            assert (
                ideal_val == result.best_values[param]
            ), f'Exp. decay fit parameter "{param}" is {result.best_values[param]} (expected: {ideal_val})'

        assert rel_err <= fit_param_rel_tol, msg


if __name__ == '__main__':
    pytest.main()
