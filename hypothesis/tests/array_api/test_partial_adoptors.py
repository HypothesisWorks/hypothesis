# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import functools
import warnings
from copy import copy
from types import SimpleNamespace

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import HypothesisWarning, InvalidArgument
from hypothesis.extra.array_api import (
    COMPLEX_NAMES,
    DTYPE_NAMES,
    FLOAT_NAMES,
    INT_NAMES,
    UINT_NAMES,
    make_strategies_namespace,
    mock_xp,
)

from tests.common.debug import check_can_generate_examples

MOCK_WARN_MSG = f"determine.*{mock_xp.__name__}.*Array API"


class MockedArray:
    def __init__(self, wrapped, *, exclude=()):
        self.wrapped = wrapped
        self.exclude = exclude

    def __getattr__(self, name):
        if name in self.exclude:
            raise AttributeError(f"removed on the mock: {name}")

        return object.__getattr__(self, name)


def wrap_array(func: callable, exclude: tuple[str, ...] = ()) -> callable:
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        result = func(*args, **kwargs)

        if isinstance(result, tuple):
            return tuple(MockedArray(arr, exclude=exclude) for arr in result)

        return MockedArray(result, exclude=exclude)

    return wrapped


def make_mock_xp(
    *, exclude: tuple[str, ...] = (), exclude_methods: tuple[str, ...] = ()
) -> SimpleNamespace:
    xp = copy(mock_xp)
    assert isinstance(exclude, tuple)  # sanity check
    assert isinstance(exclude_methods, tuple)  # sanity check
    for attr in exclude:
        delattr(xp, attr)

    array_returning_funcs = (
        "astype",
        "broadcast_arrays",
        "arange",
        "asarray",
        "empty",
        "zeros",
        "ones",
        "reshape",
        "isnan",
        "isfinite",
        "logical_or",
        "sum",
        "nonzero",
        "sort",
        "unique_values",
        "any",
        "all",
    )

    for name in array_returning_funcs:
        func = getattr(xp, name, None)
        if func is None:
            # removed in the step before
            continue
        setattr(xp, name, wrap_array(func, exclude=exclude_methods))

    return xp


def test_warning_on_noncompliant_xp():
    """Using non-compliant array modules raises helpful warning"""
    xp = make_mock_xp(exclude_methods=("__array_namespace__",))
    with pytest.warns(HypothesisWarning, match=MOCK_WARN_MSG):
        make_strategies_namespace(xp, api_version="draft")


@pytest.mark.filterwarnings(f"ignore:.*{MOCK_WARN_MSG}.*")
@pytest.mark.parametrize(
    "stratname, args, attr",
    [("from_dtype", ["int8"], "iinfo"), ("arrays", ["int8", 5], "asarray")],
)
def test_error_on_missing_attr(stratname, args, attr):
    """Strategies raise helpful error when using array modules that lack
    required attributes."""
    xp = make_mock_xp(exclude=(attr,))
    xps = make_strategies_namespace(xp, api_version="draft")
    func = getattr(xps, stratname)
    with pytest.raises(InvalidArgument, match=f"{mock_xp.__name__}.*required.*{attr}"):
        check_can_generate_examples(func(*args))


dtypeless_xp = make_mock_xp(exclude=tuple(DTYPE_NAMES))
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=HypothesisWarning)
    dtypeless_xps = make_strategies_namespace(dtypeless_xp, api_version="draft")


@pytest.mark.parametrize(
    "stratname",
    [
        "scalar_dtypes",
        "boolean_dtypes",
        "numeric_dtypes",
        "integer_dtypes",
        "unsigned_integer_dtypes",
        "floating_dtypes",
        "real_dtypes",
        "complex_dtypes",
    ],
)
def test_error_on_missing_dtypes(stratname):
    """Strategies raise helpful error when using array modules that lack
    required dtypes."""
    func = getattr(dtypeless_xps, stratname)
    with pytest.raises(InvalidArgument, match=f"{mock_xp.__name__}.*dtype.*namespace"):
        check_can_generate_examples(func())


@pytest.mark.filterwarnings(f"ignore:.*{MOCK_WARN_MSG}.*")
@pytest.mark.parametrize(
    "stratname, keep_anys",
    [
        ("scalar_dtypes", [INT_NAMES, UINT_NAMES, FLOAT_NAMES]),
        ("numeric_dtypes", [INT_NAMES, UINT_NAMES, FLOAT_NAMES, COMPLEX_NAMES]),
        ("integer_dtypes", [INT_NAMES]),
        ("unsigned_integer_dtypes", [UINT_NAMES]),
        ("floating_dtypes", [FLOAT_NAMES]),
        ("real_dtypes", [INT_NAMES, UINT_NAMES, FLOAT_NAMES]),
        ("complex_dtypes", [COMPLEX_NAMES]),
    ],
)
@given(st.data())
def test_warning_on_partial_dtypes(stratname, keep_anys, data):
    """Strategies using array modules with at least one of a dtype in the
    necessary category/categories execute with a warning."""
    exclude = []
    for keep_any in keep_anys:
        exclude.extend(
            data.draw(
                st.lists(
                    st.sampled_from(keep_any),
                    min_size=1,
                    max_size=len(keep_any) - 1,
                    unique=True,
                )
            )
        )
    xp = make_mock_xp(exclude=tuple(exclude))
    xps = make_strategies_namespace(xp, api_version="draft")
    func = getattr(xps, stratname)
    with pytest.warns(HypothesisWarning, match=f"{mock_xp.__name__}.*dtype.*namespace"):
        data.draw(func())


def test_raises_on_inferring_with_no_dunder_version():
    """When xp has no __array_api_version__, inferring api_version raises
    helpful error."""
    xp = make_mock_xp(exclude=("__array_api_version__",))
    with pytest.raises(InvalidArgument, match="has no attribute"):
        make_strategies_namespace(xp)


def test_raises_on_invalid_dunder_version():
    """When xp has invalid __array_api_version__, inferring api_version raises
    helpful error."""
    xp = make_mock_xp()
    xp.__array_api_version__ = None
    with pytest.raises(InvalidArgument):
        make_strategies_namespace(xp)
