# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

import random

import attr
import pytest

import hypothesis.internal.escalation as esc
import hypothesis.strategies as st
from hypothesis import HealthCheck, Phase, Verbosity, assume, given, note, settings
from hypothesis.internal.compat import hbytes
from hypothesis.internal.conjecture.data import Status
from hypothesis.internal.conjecture.engine import ConjectureRunner


def setup_module(module):
    esc.PREVENT_ESCALATION = True


def teardown_module(module):
    esc.PREVENT_ESCALATION = False


@attr.s()
class Write(object):
    value = attr.ib()
    child = attr.ib()


@attr.s()
class Branch(object):
    bits = attr.ib()
    children = attr.ib(default=attr.Factory(dict))


@attr.s()
class Terminal(object):
    status = attr.ib()
    payload = attr.ib(default=None)


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


def run_language_test_for(root, data, seed):
    random.seed(seed)

    def test(local_data):
        node = root
        while not isinstance(node, Terminal):
            if isinstance(node, Write):
                local_data.write(hbytes(node.value))
                node = node.child
            else:
                assert isinstance(node, Branch)
                c = local_data.draw_bits(node.bits)
                try:
                    node = node.children[c]
                except KeyError:
                    if data is None:
                        return
                    node = node.children.setdefault(c, data.draw(nodes))
        assert isinstance(node, Terminal)
        if node.status == Status.INTERESTING:
            local_data.mark_interesting(node.payload)
        elif node.status == Status.INVALID:
            local_data.mark_invalid()

    runner = ConjectureRunner(
        test,
        settings=settings(
            max_examples=1,
            buffer_size=512,
            database=None,
            suppress_health_check=HealthCheck.all(),
            verbosity=Verbosity.quiet,
            phases=list(Phase),
        ),
    )
    try:
        runner.run()
    finally:
        if data is not None:
            note(root)
    assume(runner.interesting_examples)


@settings(
    suppress_health_check=HealthCheck.all(),
    deadline=None,
    phases=set(Phase) - {Phase.shrink},
)
@given(st.data())
def test_explore_an_arbitrary_language(data):
    root = data.draw(writes | branches)
    seed = data.draw(st.integers(0, 2 ** 64 - 1))
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
