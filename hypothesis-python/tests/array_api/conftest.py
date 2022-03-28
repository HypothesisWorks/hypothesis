# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import warnings
from importlib import import_module
from os import getenv

import pytest

from hypothesis.errors import HypothesisWarning
from hypothesis.extra.array_api import make_strategies_namespace, mock_xp

from tests.array_api.common import installed_array_modules

testing_mode = getenv("HYPOTHESIS_TEST_ARRAY_API", "default")
name_to_entry_point = installed_array_modules()
with pytest.warns(HypothesisWarning):
    mock_xps = make_strategies_namespace(mock_xp)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    if testing_mode == "default":
        params = []
        try:
            xp = name_to_entry_point["numpy"].load()
            xps = make_strategies_namespace(xp)
            params = [pytest.param(xp, xps, id="numpy")]
        except KeyError:
            params = [pytest.param(mock_xp, mock_xps, id="mock")]
    elif testing_mode == "all":
        params = [pytest.param(mock_xp, mock_xps, id="mock")]
        for name, ep in name_to_entry_point.items():
            xp = ep.load()
            xps = make_strategies_namespace(xp)
            params.append(pytest.param(xp, xps, id=name))
    else:
        if testing_mode in name_to_entry_point.keys():
            xp = name_to_entry_point[testing_mode].load()
            xps = make_strategies_namespace(xp)
            params = [pytest.param(xp, xps, id=testing_mode)]
        else:
            try:
                xp = import_module(testing_mode)
                xps = make_strategies_namespace(xp)
                params = [pytest.param(xp, xps, id=testing_mode)]
            except ImportError:
                raise ValueError(
                    f"HYPOTHESIS_TEST_ARRAY_API='{testing_mode}' is not a mode "
                    "(i.e. 'default' or 'all'), name of an available entry point, "
                    "or a valid import path."
                )


def pytest_generate_tests(metafunc):
    if "xp" in metafunc.fixturenames and "xps" in metafunc.fixturenames:
        metafunc.parametrize("xp, xps", params)
