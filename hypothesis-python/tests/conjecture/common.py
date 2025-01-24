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
import sys
from contextlib import contextmanager
from typing import Optional

from hypothesis import HealthCheck, Phase, assume, settings, strategies as st
from hypothesis.control import current_build_context
from hypothesis.errors import InvalidArgument
from hypothesis.internal.conjecture import engine as engine_module
from hypothesis.internal.conjecture.choice import ChoiceT
from hypothesis.internal.conjecture.data import (
    COLLECTION_DEFAULT_MAX_SIZE,
    ConjectureData,
    IRNode,
    Status,
)
from hypothesis.internal.conjecture.engine import BUFFER_SIZE, ConjectureRunner
from hypothesis.internal.conjecture.utils import calc_label_from_name
from hypothesis.internal.entropy import deterministic_PRNG
from hypothesis.internal.escalation import InterestingOrigin
from hypothesis.internal.floats import SMALLEST_SUBNORMAL, sign_aware_lte
from hypothesis.internal.intervalsets import IntervalSet
from hypothesis.strategies._internal.strings import OneCharStringStrategy, TextStrategy

from tests.common.strategies import intervals

SOME_LABEL = calc_label_from_name("some label")


TEST_SETTINGS = settings(
    max_examples=5000, database=None, suppress_health_check=list(HealthCheck)
)


def interesting_origin(n: Optional[int] = None) -> InterestingOrigin:
    """
    Creates and returns an InterestingOrigin, parameterized by n, such that
    interesting_origin(n) == interesting_origin(m) iff n = m.

    Since n=None may by chance concide with an explicitly-passed value of n, I
    recommend not mixing interesting_origin() and interesting_origin(n) in the
    same test.
    """
    try:
        int("not an int")
    except Exception as e:
        origin = InterestingOrigin.from_exception(e)
        return origin._replace(lineno=n if n is not None else origin.lineno)


def run_to_data(f):
    with deterministic_PRNG():
        runner = ConjectureRunner(f, settings=TEST_SETTINGS)
        runner.run()
        assert runner.interesting_examples
        (last_data,) = runner.interesting_examples.values()
        return last_data


def run_to_nodes(f):
    return run_to_data(f).ir_nodes


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
                    # avoid running the explain phase in shrinker.shrink() in tests
                    # which don't test the inquisitor.
                    phases=set(settings.default.phases) - {Phase.explain},
                ),
            )
            runner.cached_test_function_ir(start)
            assert runner.interesting_examples
            (last_data,) = runner.interesting_examples.values()
            return runner.new_shrinker(
                last_data, lambda d: d.status == Status.INTERESTING
            )

    return accept


def fresh_data(*, random=None, observer=None) -> ConjectureData:
    if random is None:
        try:
            context = current_build_context()
        except InvalidArgument:
            # ensure usage of fresh_data() is not flaky outside of property tests.
            raise ValueError(
                "must pass a seeded Random instance to fresh_data() when "
                "outside of a build context"
            ) from None

        # within property tests, ensure fresh_data uses a controlled source of
        # randomness.
        # drawing this from the current build context is almost *too* magical. But
        # the alternative is an extra @given(st.randoms()) everywhere we use
        # fresh_data, so eh.
        random = context.data.draw(st.randoms())

    return ConjectureData(
        BUFFER_SIZE,
        prefix=b"",
        random=random,
        observer=observer,
    )


def clamped_shrink_towards(kwargs):
    v = kwargs["shrink_towards"]
    if kwargs["min_value"] is not None:
        v = max(kwargs["min_value"], v)
    if kwargs["max_value"] is not None:
        v = min(kwargs["max_value"], v)
    return v


@st.composite
def integer_weights(draw, min_value=None, max_value=None):
    # Sampler doesn't play well with super small floats, so exclude them
    weights = draw(
        st.dictionaries(
            st.integers(min_value=min_value, max_value=max_value),
            st.floats(0.001, 1),
            min_size=1,
            max_size=255,
        )
    )
    # invalid to have a weighting that disallows all possibilities
    assume(sum(weights.values()) != 0)
    # re-normalize probabilities to sum to some arbitrary target < 1
    target = draw(st.floats(0.001, 0.999))
    factor = target / sum(weights.values())
    weights = {k: v * factor for k, v in weights.items()}
    # float rounding error can cause this to fail.
    assume(0.001 <= sum(weights.values()) <= 0.999)
    return weights


@st.composite
def integer_kwargs(
    draw,
    *,
    use_min_value=None,
    use_max_value=None,
    use_shrink_towards=None,
    use_weights=None,
    use_forced=False,
):
    min_value = None
    max_value = None
    shrink_towards = 0
    weights = None

    if use_min_value is None:
        use_min_value = draw(st.booleans())
    if use_max_value is None:
        use_max_value = draw(st.booleans())
    use_shrink_towards = draw(st.booleans())
    if use_weights is None:
        use_weights = (
            draw(st.booleans()) if (use_min_value and use_max_value) else False
        )

    # Invariants:
    # (1) min_value <= forced <= max_value
    # (2) sum(weights.values()) < 1
    # (3) len(weights) <= 255

    if use_shrink_towards:
        shrink_towards = draw(st.integers())

    forced = draw(st.integers()) if use_forced else None
    if use_weights:
        assert use_max_value
        assert use_min_value

        min_value = draw(st.integers(max_value=forced))
        min_val = max(min_value, forced) if forced is not None else min_value
        max_value = draw(st.integers(min_value=min_val))

        weights = draw(integer_weights(min_value, max_value))
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
def _collection_kwargs(draw, *, forced, use_min_size=None, use_max_size=None):
    min_size = 0
    max_size = COLLECTION_DEFAULT_MAX_SIZE
    # collections are quite expensive in entropy. cap to avoid overruns.
    cap = 50

    if use_min_size is None:
        use_min_size = draw(st.booleans())
    if use_max_size is None:
        use_max_size = draw(st.booleans())

    if use_min_size:
        min_size = draw(
            st.integers(0, min(len(forced), cap) if forced is not None else cap)
        )

    if use_max_size:
        max_size = draw(
            st.integers(
                min_value=min_size if forced is None else max(min_size, len(forced))
            )
        )
        # cap to some reasonable max size to avoid overruns.
        max_size = min(max_size, min_size + 100)

    return {"min_size": min_size, "max_size": max_size}


@st.composite
def string_kwargs(draw, *, use_min_size=None, use_max_size=None, use_forced=False):
    # TODO also sample empty intervals, ie remove this min_size, once we handle empty
    # pseudo-choices in the ir
    interval_set = draw(intervals(min_size=1))
    forced = (
        draw(TextStrategy(OneCharStringStrategy(interval_set))) if use_forced else None
    )
    kwargs = draw(
        _collection_kwargs(
            forced=forced, use_min_size=use_min_size, use_max_size=use_max_size
        )
    )

    return {"intervals": interval_set, "forced": forced, **kwargs}


@st.composite
def bytes_kwargs(draw, *, use_min_size=None, use_max_size=None, use_forced=False):
    forced = draw(st.binary()) if use_forced else None

    kwargs = draw(
        _collection_kwargs(
            forced=forced, use_min_size=use_min_size, use_max_size=use_max_size
        )
    )
    return {"forced": forced, **kwargs}


@st.composite
def float_kwargs(draw, *, use_min_value=None, use_max_value=None, use_forced=False):
    if use_min_value is None:
        use_min_value = draw(st.booleans())
    if use_max_value is None:
        use_max_value = draw(st.booleans())

    forced = draw(st.floats()) if use_forced else None
    pivot = forced if (use_forced and not math.isnan(forced)) else None
    min_value = -math.inf
    max_value = math.inf
    smallest_nonzero_magnitude = SMALLEST_SUBNORMAL
    allow_nan = True if (use_forced and math.isnan(forced)) else draw(st.booleans())

    if use_min_value:
        min_value = draw(st.floats(max_value=pivot, allow_nan=False))

    if use_max_value:
        if pivot is None:
            min_val = min_value
        else:
            min_val = pivot if sign_aware_lte(min_value, pivot) else min_value
        max_value = draw(st.floats(min_value=min_val, allow_nan=False))

    largest_magnitude = max(abs(min_value), abs(max_value))
    # can't force something smaller than our smallest magnitude.
    if pivot is not None and pivot != 0.0:
        largest_magnitude = min(largest_magnitude, pivot)

    # avoid drawing from an empty range
    if largest_magnitude > 0:
        smallest_nonzero_magnitude = draw(
            st.floats(
                min_value=0,
                # smallest_nonzero_magnitude breaks internal clamper invariants if
                # it is allowed to be larger than the magnitude of {min, max}_value.
                max_value=largest_magnitude,
                allow_nan=False,
                exclude_min=True,
                allow_infinity=False,
            )
        )
    return {
        "min_value": min_value,
        "max_value": max_value,
        "forced": forced,
        "allow_nan": allow_nan,
        "smallest_nonzero_magnitude": smallest_nonzero_magnitude,
    }


@st.composite
def boolean_kwargs(draw, *, use_forced=False):
    forced = draw(st.booleans()) if use_forced else None
    # avoid invalid forced combinations
    p = draw(st.floats(0, 1, exclude_min=forced is True, exclude_max=forced is False))

    if 0 < p < 1:
        # match internal assumption about avoiding large draws
        bits = math.ceil(-math.log(min(p, 1 - p), 2))
        assume(bits <= 64)

    return {"p": p, "forced": forced}


def kwargs_strategy(ir_type, strategy_kwargs=None, *, use_forced=False):
    strategy = {
        "boolean": boolean_kwargs,
        "integer": integer_kwargs,
        "float": float_kwargs,
        "bytes": bytes_kwargs,
        "string": string_kwargs,
    }[ir_type]
    if strategy_kwargs is None:
        strategy_kwargs = {}
    return strategy(**strategy_kwargs.get(ir_type, {}), use_forced=use_forced)


def ir_types_and_kwargs(strategy_kwargs=None, *, use_forced=False):
    options = ["boolean", "integer", "float", "bytes", "string"]
    return st.one_of(
        st.tuples(
            st.just(name), kwargs_strategy(name, strategy_kwargs, use_forced=use_forced)
        )
        for name in options
    )


def draw_value(ir_type, kwargs):
    data = fresh_data()
    return getattr(data, f"draw_{ir_type}")(**kwargs)


@st.composite
def ir_nodes(draw, *, was_forced=None, ir_types=None):
    if ir_types is None:
        (ir_type, kwargs) = draw(ir_types_and_kwargs())
    else:
        ir_type = draw(st.sampled_from(ir_types))
        kwargs = draw(kwargs_strategy(ir_type))
    # ir nodes don't include forced in their kwargs. see was_forced attribute
    del kwargs["forced"]
    value = draw_value(ir_type, kwargs)
    was_forced = draw(st.booleans()) if was_forced is None else was_forced

    return IRNode(ir_type=ir_type, value=value, kwargs=kwargs, was_forced=was_forced)


def ir(*values: list[ChoiceT]) -> list[IRNode]:
    """
    For inline-creating an ir node or list of ir nodes, where you don't care about the
    kwargs. This uses maximally-permissable kwargs and infers the ir_type you meant
    based on the type of the value.

    You can optionally pass (value, kwargs) to as an element in order to override
    the default kwargs for that element.
    """
    mapping = {
        float: (
            "float",
            {
                "min_value": -math.inf,
                "max_value": math.inf,
                "allow_nan": True,
                "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
            },
        ),
        int: (
            "integer",
            {
                "min_value": None,
                "max_value": None,
                "weights": None,
                "shrink_towards": 0,
            },
        ),
        str: (
            "string",
            {
                "intervals": IntervalSet(((0, sys.maxunicode),)),
                "min_size": 0,
                "max_size": COLLECTION_DEFAULT_MAX_SIZE,
            },
        ),
        bytes: ("bytes", {"min_size": 0, "max_size": COLLECTION_DEFAULT_MAX_SIZE}),
        bool: ("boolean", {"p": 0.5}),
    }
    nodes = []
    for value in values:
        override_kwargs = {}
        if isinstance(value, tuple):
            (value, override_kwargs) = value
            if override_kwargs is None:
                override_kwargs = {}

        (ir_type, kwargs) = mapping[type(value)]

        nodes.append(
            IRNode(
                ir_type=ir_type,
                value=value,
                kwargs=kwargs | override_kwargs,
                was_forced=False,
            )
        )

    return tuple(nodes)


def float_kw(
    min_value=-math.inf,
    max_value=math.inf,
    *,
    allow_nan=True,
    smallest_nonzero_magnitude=SMALLEST_SUBNORMAL,
):
    return {
        "min_value": min_value,
        "max_value": max_value,
        "allow_nan": allow_nan,
        "smallest_nonzero_magnitude": smallest_nonzero_magnitude,
    }


def integer_kw(min_value=None, max_value=None, *, weights=None, shrink_towards=0):
    return {
        "min_value": min_value,
        "max_value": max_value,
        "weights": weights,
        "shrink_towards": shrink_towards,
    }


def string_kw(intervals, *, min_size=0, max_size=COLLECTION_DEFAULT_MAX_SIZE):
    return {"intervals": intervals, "min_size": min_size, "max_size": max_size}


# we could in theory define bytes_kw and boolean_kw, but without any
# default kw values they aren't really a time save.
