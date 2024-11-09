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
from types import ModuleType, SimpleNamespace

import pytest

from hypothesis.errors import HypothesisWarning, InvalidArgument
from hypothesis.extra.array_api import (
    NOMINAL_VERSIONS,
    NominalVersion,
    make_strategies_namespace,
    mock_xp,
)

from tests.array_api.common import installed_array_modules

# See README.md in regards to the env variables
test_xp_option = getenv("HYPOTHESIS_TEST_ARRAY_API", "default")

test_version_option = getenv("HYPOTHESIS_TEST_ARRAY_API_VERSION", "default")
if test_version_option != "default" and test_version_option not in NOMINAL_VERSIONS:
    raise ValueError(
        f"HYPOTHESIS_TEST_ARRAY_API_VERSION='{test_version_option}' is not "
        f"'default' or a valid api_version {NOMINAL_VERSIONS}."
    )
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=HypothesisWarning)
    mock_version = "draft" if test_version_option == "default" else test_version_option
    mock_xps = make_strategies_namespace(mock_xp, api_version=mock_version)
api_version = None if test_version_option == "default" else test_version_option


class InvalidArgumentWarning(UserWarning):
    """Custom warning so we can bypass our global capturing"""


name_to_entry_point = installed_array_modules()
xp_and_xps_pairs: list[tuple[ModuleType, SimpleNamespace]] = []
with warnings.catch_warnings():
    # We ignore all warnings here as many array modules warn on import. Ideally
    # we would just ignore ImportWarning, but no one seems to use it!
    warnings.simplefilter("ignore")
    warnings.simplefilter("default", category=InvalidArgumentWarning)
    # We go through the steps described in README.md to define `xp_xps_pairs`,
    # which contains the array module(s) to be run against the test suite, along
    # with their respective strategy namespaces.
    if test_xp_option == "default":
        xp_and_xps_pairs = [(mock_xp, mock_xps)]
    elif test_xp_option == "all":
        if len(name_to_entry_point) == 0:
            raise ValueError(
                "HYPOTHESIS_TEST_ARRAY_API='all', but no entry points where found"
            )
        xp_and_xps_pairs = [(mock_xp, mock_xps)]
        for ep in name_to_entry_point.values():
            xp = ep.load()
            try:
                xps = make_strategies_namespace(xp, api_version=api_version)
            except InvalidArgument as e:
                warnings.warn(str(e), InvalidArgumentWarning, stacklevel=1)
            else:
                xp_and_xps_pairs.append((xp, xps))
    elif test_xp_option in name_to_entry_point:
        ep = name_to_entry_point[test_xp_option]
        xp = ep.load()
        xps = make_strategies_namespace(xp, api_version=api_version)
        xp_and_xps_pairs = [(xp, xps)]
    else:
        try:
            xp = import_module(test_xp_option)
        except ImportError as e:
            raise ValueError(
                f"HYPOTHESIS_TEST_ARRAY_API='{test_xp_option}' is not a valid "
                "option ('default' or 'all'), name of an available entry point, "
                "or a valid import path."
            ) from e
        else:
            xps = make_strategies_namespace(xp, api_version=api_version)
            xp_and_xps_pairs = [(xp, xps)]


def pytest_generate_tests(metafunc):
    xp_params = []
    xp_and_xps_params = []
    for xp, xps in xp_and_xps_pairs:
        xp_params.append(pytest.param(xp, id=xp.__name__))
        xp_and_xps_params.append(
            pytest.param(xp, xps, id=f"{xp.__name__}-{xps.api_version}")
        )
    if "xp" in metafunc.fixturenames:
        if "xps" in metafunc.fixturenames:
            metafunc.parametrize("xp, xps", xp_and_xps_params)
        else:
            metafunc.parametrize("xp", xp_params)


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "xps" in item.fixturenames:
            markers = [m for m in item.own_markers if m.name == "xp_min_version"]
            if markers:
                assert len(markers) == 1  # sanity check
                min_version: NominalVersion = markers[0].args[0]
                xps_version: NominalVersion = item.callspec.params["xps"].api_version
                if xps_version < min_version:
                    item.add_marker(
                        pytest.mark.skip(reason=f"requires api_version=>{min_version}")
                    )
