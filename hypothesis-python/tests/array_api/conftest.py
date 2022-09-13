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

with pytest.warns(HypothesisWarning):
    mock_xps = make_strategies_namespace(mock_xp, api_version="draft")

# See README.md in regards to the HYPOTHESIS_TEST_ARRAY_API env variable
test_xp_option = getenv("HYPOTHESIS_TEST_ARRAY_API", "default")
name_to_entry_point = installed_array_modules()
with warnings.catch_warnings():
    # We ignore all warnings here as many array modules warn on import
    warnings.simplefilter("ignore")
    # We go through the steps described in README.md to define `params`, which
    # contains the array module(s) to be ran against the test suite.
    # Specifically `params` is a list of pytest parameters, with each parameter
    # containing the array module and its respective strategies namespace.
    if test_xp_option == "default":
        try:
            xp = name_to_entry_point["numpy"].load()
            xps = make_strategies_namespace(xp)
            params = [pytest.param(xp, xps, id=f"numpy-{xps.api_version}")]
        except KeyError:
            params = [pytest.param(mock_xp, mock_xps, id="mock")]
    elif test_xp_option == "all":
        if len(name_to_entry_point) == 0:
            raise ValueError(
                "HYPOTHESIS_TEST_ARRAY_API='all', but no entry points where found"
            )
        params = [pytest.param(mock_xp, mock_xps, id="mock-draft")]
        for name, ep in name_to_entry_point.items():
            xp = ep.load()
            xps = make_strategies_namespace(xp)
            params.append(pytest.param(xp, xps, id=f"{name}-{xps.api_version}"))
    elif test_xp_option in name_to_entry_point.keys():
        ep = name_to_entry_point[test_xp_option]
        xp = ep.load()
        xps = make_strategies_namespace(xp)
        params = [pytest.param(xp, xps, id=f"{test_xp_option}-{xps.api_version}")]
    else:
        try:
            xp = import_module(test_xp_option)
            xps = make_strategies_namespace(xp)
            params = [pytest.param(xp, xps, id=f"{test_xp_option}-{xps.api_version}")]
        except ImportError as e:
            raise ValueError(
                f"HYPOTHESIS_TEST_ARRAY_API='{test_xp_option}' is not a valid "
                "option ('default' or 'all'), name of an available entry point, "
                "or a valid import path."
            ) from e


def pytest_generate_tests(metafunc):
    if "xp" in metafunc.fixturenames and "xps" in metafunc.fixturenames:
        metafunc.parametrize("xp, xps", params)
