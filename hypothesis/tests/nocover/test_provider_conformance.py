# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""
Conformance tests for the remaining in-tree providers, and a rogues' gallery of
deliberately-broken providers which run_conformance_test must reject. The
latter is how we know the conformance test itself stays strong: each rogue
reintroduces a real or plausible provider bug.
"""

import math
import sys
import warnings
from contextlib import contextmanager

import pytest

from hypothesis import Phase, settings, strategies as st
from hypothesis.errors import StopTest
from hypothesis.internal.compat import WINDOWS
from hypothesis.internal.conjecture.provider_conformance import (
    _run_findability_tests,
    run_conformance_test,
)
from hypothesis.internal.conjecture.providers import (
    COLLECTION_DEFAULT_MAX_SIZE,
    BytestringProvider,
    HypothesisProvider,
    URandomProvider,
)

from tests.conjecture.test_provider import PrngProvider

_conformance_settings = settings(max_examples=20, stateful_step_count=20)


def run_conformance(provider, **kwargs):
    kwargs.setdefault("settings", _conformance_settings)
    with warnings.catch_warnings():
        # emitted by available_timezones() from st.timezone_keys() on 3.11+
        # with tzdata installed. see https://github.com/python/cpython/issues/137841.
        # Once cpython fixes this, we can remove this.
        if sys.version_info >= (3, 11):
            warnings.simplefilter("ignore", EncodingWarning)
        run_conformance_test(provider, **kwargs)


class ObservingHypothesisProvider(HypothesisProvider):
    def observe_information_messages(self, *, lifetime):
        yield {"type": "info", "title": "observing-provider", "content": {}}


@pytest.mark.parametrize(
    "provider",
    [
        HypothesisProvider,
        ObservingHypothesisProvider,
        pytest.param(
            URandomProvider,
            marks=pytest.mark.skipif(
                WINDOWS, reason="/dev/urandom not available on windows"
            ),
        ),
    ],
)
def test_provider_conformance(provider):
    run_conformance(provider)


class NoNegativeIntegersProvider(BytestringProvider):
    # The exact BytestringProvider.draw_integer bug reported in issue #4847:
    # drawn bits were compared against the bounds without being offset by
    # min_value, so negative values were unreachable and fully-negative ranges
    # always overran.
    def draw_integer(
        self, min_value=None, max_value=None, *, weights=None, shrink_towards=0
    ):
        if min_value is None and max_value is None:
            min_value = -(2**127)
            max_value = 2**127 - 1
        elif min_value is None:
            min_value = max_value - 2**64
        elif max_value is None:
            max_value = min_value + 2**64

        if min_value == max_value:
            return min_value

        bits = (max_value - min_value).bit_length()
        value = self._draw_bits(bits)
        while not (min_value <= value <= max_value):
            value = self._draw_bits(bits)
        return value


def test_rejects_unfindable_negative_integers():
    # sound in the interface sense, so run just the findability checks, with a
    # small budget since most integer targets will exhaust it.
    with pytest.raises(AssertionError, match="could not generate"):
        _run_findability_tests(
            NoNegativeIntegersProvider,
            st.fixed_dictionaries({"bytestring": st.binary()}),
            (),
            find_settings=settings(max_examples=50),
        )


class BoolIntegerProvider(PrngProvider):
    def draw_integer(self, *args, **kwargs):
        return bool(super().draw_integer(*args, **kwargs))


class NanFloatProvider(PrngProvider):
    def draw_float(self, **kwargs):
        return math.nan


class IntervalIgnoringProvider(PrngProvider):
    def draw_string(
        self, intervals, *, min_size=0, max_size=COLLECTION_DEFAULT_MAX_SIZE
    ):
        return "a" * max(min_size, 1)


class StuckBooleanProvider(PrngProvider):
    def draw_boolean(self, p=0.5):
        return False


class UnconcludedStopTestProvider(BytestringProvider):
    def draw_float(self, **kwargs):
        raise StopTest(self._cd.testcounter)


class SpinningProvider(PrngProvider):
    def draw_bytes(self, min_size=0, max_size=COLLECTION_DEFAULT_MAX_SIZE):
        while True:
            self.draw_boolean()


class SwallowingProvider(PrngProvider):
    # suppresses exceptions it never declared, which would hide failing tests
    def draw_float(self, **kwargs):
        raise RuntimeError("provider bug")

    @contextmanager
    def per_test_case_context_manager(self):
        try:
            yield
        except RuntimeError:
            pass


class WeightsMutatingProvider(PrngProvider):
    def draw_integer(
        self, min_value=None, max_value=None, *, weights=None, shrink_towards=0
    ):
        if weights is not None:
            weights.clear()
        return super().draw_integer(
            min_value, max_value, weights=weights, shrink_towards=shrink_towards
        )


@pytest.mark.parametrize(
    "provider, provider_kw, match",
    [
        (BoolIntegerProvider, None, "got bool"),
        (NanFloatProvider, None, "not permitted"),
        (IntervalIgnoringProvider, None, "not permitted"),
        # p is advisory except at p=0 and p=1, where it is a hard requirement
        (StuckBooleanProvider, None, "not permitted"),
        (
            UnconcludedStopTestProvider,
            {"bytestring": st.binary(min_size=50)},
            "without concluding",
        ),
        (SpinningProvider, None, "unbounded drawing loop"),
        (SwallowingProvider, None, "would hide failing tests"),
        (WeightsMutatingProvider, None, "mutated its weights"),
    ],
)
def test_rejects_nonconforming_providers(provider, provider_kw, match):
    with pytest.raises(AssertionError, match=match):
        run_conformance(
            provider,
            provider_kw=provider_kw,
            check_findability=False,
            # derandomize so that, having seen these tests find each bug once,
            # we know they always will. We only need detection, not a minimal
            # example, so skip the shrink phase.
            settings=settings(
                max_examples=50,
                stateful_step_count=50,
                derandomize=True,
                phases=[Phase.generate],
            ),
        )
