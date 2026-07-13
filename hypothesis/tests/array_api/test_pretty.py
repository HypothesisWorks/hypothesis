# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from inspect import signature

import pytest

from hypothesis.errors import InvalidArgument
from hypothesis.extra import array_api
from hypothesis.extra.array_api import make_strategies_namespace

from tests.array_api.common import MIN_VER_FOR_COMPLEX


@pytest.mark.parametrize(
    "name",
    [
        "from_dtype",
        "arrays",
        "array_shapes",
        "scalar_dtypes",
        "boolean_dtypes",
        "numeric_dtypes",
        "integer_dtypes",
        "unsigned_integer_dtypes",
        "floating_dtypes",
        "real_dtypes",
        pytest.param(
            "complex_dtypes", marks=pytest.mark.xp_min_version(MIN_VER_FOR_COMPLEX)
        ),
        "valid_tuple_axes",
        "broadcastable_shapes",
        "mutually_broadcastable_shapes",
        "indices",
    ],
)
def test_namespaced_methods_meta(xp, xps, name):
    """Namespaced method objects have good meta attributes."""
    func = getattr(xps, name)
    assert func.__name__ == name
    assert func.__doc__ is not None
    # The (private) top-level strategy methods may expose a xp argument in their
    # function signatures. make_strategies_namespace() exists to wrap these
    # top-level methods by binding the passed xp argument, and so the namespace
    # it returns should not expose xp in any of its function signatures.
    assert "xp" not in signature(func).parameters


@pytest.mark.parametrize(
    "name, valid_args",
    [
        ("from_dtype", ["int8"]),
        ("arrays", ["int8", 5]),
        ("array_shapes", []),
        ("scalar_dtypes", []),
        ("boolean_dtypes", []),
        ("numeric_dtypes", []),
        ("integer_dtypes", []),
        ("unsigned_integer_dtypes", []),
        ("floating_dtypes", []),
        ("real_dtypes", []),
        pytest.param(
            "complex_dtypes", [], marks=pytest.mark.xp_min_version(MIN_VER_FOR_COMPLEX)
        ),
        ("valid_tuple_axes", [0]),
        ("broadcastable_shapes", [()]),
        ("mutually_broadcastable_shapes", [3]),
        ("indices", [(5,)]),
    ],
)
def test_namespaced_strategies_repr(xp, xps, name, valid_args):
    """Namespaced strategies have good repr."""
    func = getattr(xps, name)
    strat = func(*valid_args)
    assert repr(strat).startswith(name + "("), f"{name} not in strat repr {strat!r}"
    assert len(repr(strat)) < 100, "strat repr looks too long"
    assert xp.__name__ not in repr(strat), f"{xp.__name__} in strat repr"


@pytest.mark.filterwarnings("ignore::hypothesis.errors.HypothesisWarning")
def test_inferred_version_strategies_namespace_repr(xp):
    """Strategies namespace has good repr when api_version=None."""
    try:
        xps = make_strategies_namespace(xp)
    except InvalidArgument as e:
        pytest.skip(str(e))
    expected = f"make_strategies_namespace({xp.__name__})"
    assert repr(xps) == expected
    assert str(xps) == expected


@pytest.mark.filterwarnings("ignore::hypothesis.errors.HypothesisWarning")
def test_specified_version_strategies_namespace_repr(xp, monkeypatch):
    """Strategies namespace has good repr when api_version is specified."""
    monkeypatch.setattr(array_api, "_args_to_xps", {})  # ignore cached versions
    xps = make_strategies_namespace(xp, api_version="2021.12")
    expected = f"make_strategies_namespace({xp.__name__}, api_version='2021.12')"
    assert repr(xps) == expected
    assert str(xps) == expected
