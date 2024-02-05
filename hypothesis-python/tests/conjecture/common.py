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
from contextlib import contextmanager
from random import Random

from hypothesis import HealthCheck, assume, settings, strategies as st
from hypothesis.internal.conjecture import engine as engine_module
from hypothesis.internal.conjecture.data import ConjectureData, Status
from hypothesis.internal.conjecture.engine import BUFFER_SIZE, ConjectureRunner
from hypothesis.internal.conjecture.utils import calc_label_from_name
from hypothesis.internal.entropy import deterministic_PRNG
from hypothesis.strategies._internal.strings import OneCharStringStrategy, TextStrategy

from tests.common.strategies import intervals

SOME_LABEL = calc_label_from_name("some label")


TEST_SETTINGS = settings(
    max_examples=5000, database=None, suppress_health_check=list(HealthCheck)
)


def run_to_data(f):
    with deterministic_PRNG():
        runner = ConjectureRunner(f, settings=TEST_SETTINGS)
        runner.run()
        assert runner.interesting_examples
        (last_data,) = runner.interesting_examples.values()
        return last_data


def run_to_buffer(f):
    return bytes(run_to_data(f).buffer)


@contextmanager
def buffer_size_limit(n):
    original = engine_module.BUFFER_SIZE
    try:
        engine_module.BUFFER_SIZE = n
        yield
    finally:
        engine_module.BUFFER_SIZE = original


def shrinking_from(start):
    def accept(f):
        with deterministic_PRNG():
            runner = ConjectureRunner(
                f,
                settings=settings(
                    max_examples=5000,
                    database=None,
                    suppress_health_check=list(HealthCheck),
                ),
            )
            runner.cached_test_function(start)
            assert runner.interesting_examples
            (last_data,) = runner.interesting_examples.values()
            return runner.new_shrinker(
                last_data, lambda d: d.status == Status.INTERESTING
            )

    return accept


def fresh_data(*, observer=None) -> ConjectureData:
    return ConjectureData(BUFFER_SIZE, prefix=b"", random=Random(), observer=observer)


@st.composite
def draw_integer_kwargs(
    draw,
    *,
    use_min_value=True,
    use_max_value=True,
    use_shrink_towards=True,
    use_weights=True,
    use_forced=False,
):
    min_value = None
    max_value = None
    shrink_towards = 0
    weights = None

    # this generation is complicated to deal with maintaining any combination of
    # the following invariants, depending on which parameters are passed:
    #
    # (1) min_value <= forced <= max_value
    # (2) max_value - min_value + 1 == len(weights)
    # (3) len(weights) <= 255

    forced = draw(st.integers()) if use_forced else None
    if use_weights:
        assert use_max_value
        assert use_min_value
        # handle the weights case entirely independently from the non-weights case.
        # We'll treat the weights as our "key" draw and base all other draws on that.

        # weights doesn't play well with super small floats, so exclude <.01
        weights = draw(st.lists(st.floats(0.01, 1), min_size=1, max_size=255))

        # we additionally pick a central value (if not forced), and then the index
        # into the weights at which it can be found - aka the min-value offset.
        center = forced if use_forced else draw(st.integers())
        min_value = center - draw(st.integers(0, len(weights) - 1))
        max_value = min_value + len(weights) - 1
    else:
        if use_min_value:
            min_value = draw(st.integers(max_value=forced))
        if use_max_value:
            min_vals = []
            if min_value is not None:
                min_vals.append(min_value)
            if forced is not None:
                min_vals.append(forced)
            min_val = max(min_vals) if min_vals else None
            max_value = draw(st.integers(min_value=min_val))

    if use_shrink_towards:
        shrink_towards = draw(st.integers())

    if forced is not None:
        assume((forced - shrink_towards).bit_length() < 128)

    return {
        "min_value": min_value,
        "max_value": max_value,
        "shrink_towards": shrink_towards,
        "weights": weights,
        "forced": forced,
    }


@st.composite
def draw_string_kwargs(draw, *, use_min_size=True, use_max_size=True, use_forced=False):
    interval_set = draw(intervals())
    # TODO relax this restriction once we handle empty pseudo-choices in the ir
    assume(len(interval_set) > 0)
    forced = (
        draw(TextStrategy(OneCharStringStrategy(interval_set))) if use_forced else None
    )

    min_size = 0
    max_size = None

    if use_min_size:
        # cap to some reasonable min size to avoid overruns.
        n = 100
        if forced is not None:
            n = min(n, len(forced))

        min_size = draw(st.integers(0, n))

    if use_max_size:
        n = min_size if forced is None else max(min_size, len(forced))
        max_size = draw(st.integers(min_value=n))
        # cap to some reasonable max size to avoid overruns.
        max_size = min(max_size, min_size + 100)

    return {
        "intervals": interval_set,
        "min_size": min_size,
        "max_size": max_size,
        "forced": forced,
    }


@st.composite
def draw_bytes_kwargs(draw, *, use_forced=False):
    forced = draw(st.binary()) if use_forced else None
    # be reasonable with the number of bytes we ask for. We only have BUFFER_SIZE
    # to work with before we overrun.
    size = (
        draw(st.integers(min_value=0, max_value=100)) if forced is None else len(forced)
    )

    return {"size": size, "forced": forced}


@st.composite
def draw_float_kwargs(
    draw, *, use_min_value=True, use_max_value=True, use_forced=False
):
    forced = draw(st.floats()) if use_forced else None
    pivot = forced if (use_forced and not math.isnan(forced)) else None
    min_value = -math.inf
    max_value = math.inf

    if use_min_value:
        min_value = draw(st.floats(max_value=pivot, allow_nan=False))

    if use_max_value:
        min_val = min_value if not pivot is not None else max(min_value, pivot)
        max_value = draw(st.floats(min_value=min_val, allow_nan=False))

    return {"min_value": min_value, "max_value": max_value, "forced": forced}


@st.composite
def draw_boolean_kwargs(draw, *, use_forced=False):
    forced = draw(st.booleans()) if use_forced else None
    p = draw(st.floats(0, 1, allow_nan=False, allow_infinity=False))

    # avoid invalid forced combinations
    assume(p > 0 or forced is False)
    assume(p < 1 or forced is True)

    if 0 < p < 1:
        # match internal assumption about avoiding large draws
        bits = math.ceil(-math.log(min(p, 1 - p), 2))
        assume(bits <= 64)

    return {"p": p, "forced": forced}
