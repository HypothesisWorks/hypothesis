# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import math

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.internal.conjecture import providers
from hypothesis.internal.conjecture.choice import choice_equal
from hypothesis.internal.conjecture.providers import CONSTANTS_CACHE
from hypothesis.internal.constants_ast import Constants

from tests.common.debug import find_any
from tests.common.utils import Why, xfail_on_crosshair


# I tried using @given(st.integers()) here, but I think there is a bad interaction
# with CONSTANTS_CACHE when testing it inside of a hypothesis test.
@pytest.mark.parametrize("value", [2**20 - 50, 2**10 - 10, 129387123, -19827321, 0])
def test_can_draw_local_constants_integers(monkeypatch, value):
    # _get_local_constants normally invalidates this cache for us, but we're
    # monkeypatching it.
    CONSTANTS_CACHE.cache.clear()
    monkeypatch.setattr(
        providers, "_get_local_constants", lambda: Constants(integers={value})
    )
    find_any(st.integers(), lambda v: choice_equal(v, value))


@xfail_on_crosshair(Why.undiscovered)  # I think float_to_int is difficult for crosshair
@pytest.mark.parametrize("value", [1.2938, -1823.0239, 1e999, math.nan])
def test_can_draw_local_constants_floats(monkeypatch, value):
    CONSTANTS_CACHE.cache.clear()
    monkeypatch.setattr(
        providers, "_get_local_constants", lambda: Constants(floats={value})
    )
    find_any(st.floats(), lambda v: choice_equal(v, value))


@pytest.mark.parametrize("value", [b"abdefgh", b"a" * 50])
def test_can_draw_local_constants_bytes(monkeypatch, value):
    CONSTANTS_CACHE.cache.clear()
    monkeypatch.setattr(
        providers, "_get_local_constants", lambda: Constants(bytes={value})
    )
    find_any(st.binary(), lambda v: choice_equal(v, value))


@pytest.mark.parametrize("value", ["abdefgh", "a" * 50])
def test_can_draw_local_constants_string(monkeypatch, value):
    CONSTANTS_CACHE.cache.clear()
    monkeypatch.setattr(
        providers, "_get_local_constants", lambda: Constants(strings={value})
    )
    # we have a bunch of strings in GLOBAL_CONSTANTS, so it might take a while
    # to generate our local constant.
    find_any(
        st.text(),
        lambda v: choice_equal(v, value),
        settings=settings(max_examples=5_000),
    )


def test_actual_collection(monkeypatch):
    # covering test for doing some real work collecting constants. We'll fake
    # hypothesis as being the "local" module, just to get some real constant
    # collection going.

    # reset cache checks
    monkeypatch.setattr(providers, "_sys_modules_len", None)
    monkeypatch.setattr(providers, "_seen_modules", set())
    monkeypatch.setattr(providers, "is_local_module_file", lambda f: "hypothesis" in f)

    @given(st.integers())
    def f(n):
        pass

    f()
