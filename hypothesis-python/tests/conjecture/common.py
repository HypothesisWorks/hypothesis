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

from hypothesis import HealthCheck, Phase, settings, strategies as st
from hypothesis.control import current_build_context, currently_in_test_context
from hypothesis.internal.conjecture import engine as engine_module
from hypothesis.internal.conjecture.choice import ChoiceNode, ChoiceT
from hypothesis.internal.conjecture.data import ConjectureData, Status
from hypothesis.internal.conjecture.engine import ConjectureRunner
from hypothesis.internal.conjecture.provider_conformance import (
    choice_types_constraints,
    constraints_strategy,
)
from hypothesis.internal.conjecture.providers import COLLECTION_DEFAULT_MAX_SIZE
from hypothesis.internal.conjecture.utils import calc_label_from_name
from hypothesis.internal.entropy import deterministic_PRNG
from hypothesis.internal.escalation import InterestingOrigin
from hypothesis.internal.floats import SMALLEST_SUBNORMAL
from hypothesis.internal.intervalsets import IntervalSet

SOME_LABEL = calc_label_from_name("some label")


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
        runner = ConjectureRunner(
            f,
            settings=settings(
                max_examples=300, database=None, suppress_health_check=list(HealthCheck)
            ),
        )
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


def draw_value(choice_type, constraints):
    data = fresh_data()
    return getattr(data, f"draw_{choice_type}")(**constraints)


@st.composite
def choices(draw):
    (choice_type, constraints) = draw(choice_types_constraints())
    return draw_value(choice_type, constraints)


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
