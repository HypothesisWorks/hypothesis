# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import random
from dataclasses import dataclass, field
from typing import Any

import pytest

from hypothesis import (
    HealthCheck,
    Phase,
    Verbosity,
    assume,
    given,
    note,
    settings,
    strategies as st,
)
from hypothesis.internal.conjecture.data import Status
from hypothesis.internal.conjecture.engine import ConjectureRunner

from tests.common.utils import Why, xfail_on_crosshair
from tests.conjecture.common import interesting_origin


@dataclass
class Write:
    value: Any
    child: Any


@dataclass
class Branch:
    bits: Any
    children: Any = field(default_factory=dict)


@dataclass
class Terminal:
    status: Any
    payload: Any = field(default=None)


nodes = st.deferred(lambda: terminals | writes | branches)


# Does not include Status.OVERFLOW by design: That happens because of the size
# of the string, not the input language.
terminals = st.one_of(
    st.just(Terminal(Status.VALID)),
    st.just(Terminal(Status.INVALID)),
    st.builds(Terminal, status=st.just(Status.INTERESTING), payload=st.integers(0, 10)),
)

branches = st.builds(Branch, bits=st.integers(1, 64))

writes = st.builds(Write, value=st.binary(min_size=1), child=nodes)


# Remember what the default phases are with no test running, so that we can
# run an outer test with non-default phases and then restore the defaults for
# the inner test.
_default_phases = settings.default.phases


def run_language_test_for(root, data, seed):
    random.seed(seed)

    def test(local_data):
        node = root
        while not isinstance(node, Terminal):
            if isinstance(node, Write):
                local_data.draw_bytes(
                    len(node.value), len(node.value), forced=node.value
                )
                node = node.child
            else:
                assert isinstance(node, Branch)
                c = local_data.draw_integer(0, 2**node.bits - 1)
                try:
                    node = node.children[c]
                except KeyError:
                    if data is None:
                        return
                    node = node.children.setdefault(c, data.draw(nodes))
        assert isinstance(node, Terminal)
        if node.status == Status.INTERESTING:
            local_data.mark_interesting(interesting_origin(node.payload))
        elif node.status == Status.INVALID:
            local_data.mark_invalid()

    runner = ConjectureRunner(
        test,
        settings=settings(
            max_examples=1,
            database=None,
            suppress_health_check=list(HealthCheck),
            verbosity=Verbosity.quiet,
            # Restore the global default phases, so that we don't inherit the
            # phases setting from the outer test.
            phases=_default_phases,
        ),
    )
    try:
        runner.run()
    finally:
        if data is not None:
            note(root)
    assume(runner.interesting_examples)


@xfail_on_crosshair(Why.nested_given)  # technically nested-engine, but same problem
@settings(
    suppress_health_check=list(HealthCheck),
    deadline=None,
    phases=set(settings.default.phases) - {Phase.shrink},
)
@given(st.data())
def test_explore_an_arbitrary_language(data):
    root = data.draw(writes | branches)
    seed = data.draw(st.integers(0, 2**64 - 1))
    run_language_test_for(root, data, seed)


@pytest.mark.parametrize("seed, language", [])
def test_run_specific_example(seed, language):
    """This test recreates individual languages generated with the main test.

    These are typically manually pruned down a bit - e.g. it's
    OK to remove VALID nodes because KeyError is treated as if it lead to one
    in this test (but not in the @given test).

    These tests are likely to be fairly fragile with respect to changes in the
    underlying engine. Feel free to delete examples if they start failing after
    a change.
    """
    run_language_test_for(language, None, seed)
