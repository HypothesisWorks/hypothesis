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
from random import Random
from typing import Optional

from hypothesis import HealthCheck, Phase, assume, settings, strategies as st
from hypothesis.control import current_build_context, currently_in_test_context
from hypothesis.internal.conjecture import engine as engine_module
from hypothesis.internal.conjecture.choice import ChoiceNode, ChoiceT
from hypothesis.internal.conjecture.data import ConjectureData, Status
from hypothesis.internal.conjecture.engine import ConjectureRunner
from hypothesis.internal.conjecture.providers import COLLECTION_DEFAULT_MAX_SIZE
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
    return run_to_data(f).nodes


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
            runner.cached_test_function(start)
            assert runner.interesting_examples
            (last_data,) = runner.interesting_examples.values()
            return runner.new_shrinker(
                last_data, lambda d: d.status == Status.INTERESTING
            )

    return accept


def fresh_data(*, random=None, observer=None) -> ConjectureData:
    # support importing this file from our nose job, which doesn't have pytest
    import pytest

    context = current_build_context() if currently_in_test_context() else None
    if context is not None and settings().backend == "crosshair":
        # we should reeaxmine fresh_data sometime and see if we can replace it
        # with nicer and higher level hypothesis idioms.
        #
        # For now it doesn't work well with crosshair tests. This is no big
        # loss, because these tests often rely on hypothesis-provider-specific
        # things.
        pytest.skip(
            "Fresh data is too low level (and too much of a hack) to be "
            "worth supporting when testing with crosshair"
        )

    if random is None:
        if context is None:
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

        # @example uses a zero-length data, which means we can't use a
        # hypothesis-backed random (which would entail drawing from the data).
        # In this case, use a deterministic Random(0).
        random = (
            context.data.draw(st.randoms(use_true_random=True))
            if (choices := context.data.max_choices) is None or choices > 0
            else Random(0)
        )

    return ConjectureData(random=random, observer=observer)


def clamped_shrink_towards(constraints):
    v = constraints["shrink_towards"]
    if constraints["min_value"] is not None:
        v = max(constraints["min_value"], v)
    if constraints["max_value"] is not None:
        v = min(constraints["max_value"], v)
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
def integer_constraints(
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
def _collection_constraints(draw, *, forced, use_min_size=None, use_max_size=None):
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
        if forced is None:
            # cap to some reasonable max size to avoid overruns.
            max_size = min(max_size, min_size + 100)

    return {"min_size": min_size, "max_size": max_size}


@st.composite
def string_constraints(draw, *, use_min_size=None, use_max_size=None, use_forced=False):
    interval_set = draw(intervals())
    forced = (
        draw(TextStrategy(OneCharStringStrategy(interval_set))) if use_forced else None
    )
    constraints = draw(
        _collection_constraints(
            forced=forced, use_min_size=use_min_size, use_max_size=use_max_size
        )
    )
    # if the intervalset is empty, then the min size must be zero, because the
    # only valid value is the empty string.
    if len(interval_set) == 0:
        constraints["min_size"] = 0

    return {"intervals": interval_set, "forced": forced, **constraints}


@st.composite
def bytes_constraints(draw, *, use_min_size=None, use_max_size=None, use_forced=False):
    forced = draw(st.binary()) if use_forced else None

    constraints = draw(
        _collection_constraints(
            forced=forced, use_min_size=use_min_size, use_max_size=use_max_size
        )
    )
    return {"forced": forced, **constraints}


@st.composite
def float_constraints(
    draw, *, use_min_value=None, use_max_value=None, use_forced=False
):
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
def boolean_constraints(draw, *, use_forced=False):
    forced = draw(st.booleans()) if use_forced else None
    # avoid invalid forced combinations
    p = draw(st.floats(0, 1, exclude_min=forced is True, exclude_max=forced is False))

    return {"p": p, "forced": forced}


def constraints_strategy(choice_type, strategy_constraints=None, *, use_forced=False):
    strategy = {
        "boolean": boolean_constraints,
        "integer": integer_constraints,
        "float": float_constraints,
        "bytes": bytes_constraints,
        "string": string_constraints,
    }[choice_type]
    if strategy_constraints is None:
        strategy_constraints = {}
    return strategy(**strategy_constraints.get(choice_type, {}), use_forced=use_forced)


def choice_types_constraints(strategy_constraints=None, *, use_forced=False):
    options = ["boolean", "integer", "float", "bytes", "string"]
    return st.one_of(
        st.tuples(
            st.just(name),
            constraints_strategy(name, strategy_constraints, use_forced=use_forced),
        )
        for name in options
    )


def draw_value(choice_type, constraints):
    data = fresh_data()
    return getattr(data, f"draw_{choice_type}")(**constraints)


@st.composite
def nodes(draw, *, was_forced=None, choice_types=None):
    if choice_types is None:
        (choice_type, constraints) = draw(choice_types_constraints())
    else:
        choice_type = draw(st.sampled_from(choice_types))
        constraints = draw(constraints_strategy(choice_type))
    # choice nodes don't include forced in their constraints. see was_forced attribute
    del constraints["forced"]
    value = draw_value(choice_type, constraints)
    was_forced = draw(st.booleans()) if was_forced is None else was_forced

    return ChoiceNode(
        type=choice_type, value=value, constraints=constraints, was_forced=was_forced
    )


def nodes_inline(*values: list[ChoiceT]) -> list[ChoiceNode]:
    """
    For inline-creating a choice node or list of choice nodes, where you don't
    care about the constraints. This uses maximally-permissable constraints and
    infers the choice_type you meant based on the type of the value.

    You can optionally pass (value, constraints) to as an element in order to override
    the default constraints for that element.
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
        override_constraints = {}
        if isinstance(value, tuple):
            (value, override_constraints) = value
            if override_constraints is None:
                override_constraints = {}

        (choice_type, constraints) = mapping[type(value)]

        nodes.append(
            ChoiceNode(
                type=choice_type,
                value=value,
                constraints=constraints | override_constraints,
                was_forced=False,
            )
        )

    return tuple(nodes)


def float_constr(
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


def integer_constr(min_value=None, max_value=None, *, weights=None, shrink_towards=0):
    return {
        "min_value": min_value,
        "max_value": max_value,
        "weights": weights,
        "shrink_towards": shrink_towards,
    }


def string_constr(intervals, *, min_size=0, max_size=COLLECTION_DEFAULT_MAX_SIZE):
    return {"intervals": intervals, "min_size": min_size, "max_size": max_size}


# we could in theory define bytes_constr and boolean_constr, but without any
# default kw values they aren't really a time save.
