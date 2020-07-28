# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

from hypothesis.internal.conjecture.dfa import ConcreteDFA


def test_enumeration_when_sizes_do_not_agree():
    dfa = ConcreteDFA([{0: 1, 1: 2}, {}, {1: 3}, {}], {1, 3})  # 0  # 1  # 2  # 3

    assert list(dfa.all_matching_strings()) == [b"\0", b"\1\1"]


def test_enumeration_of_very_long_strings():
    """This test is mainly testing that it terminates. If we were
    to use a naive breadth first search for this it would take
    forever to run because it would run in time roughly 256 ** 50.
    """
    size = 50
    dfa = ConcreteDFA(
        [{c: n + 1 for c in range(256)} for n in range(100)] + [{}], {size}
    )

    for i, s in enumerate(dfa.all_matching_strings()):
        assert len(s) == size
        assert int.from_bytes(s, "big") == i
        if i >= 1000:
            break


def test_max_length_of_empty_dfa_is_zero():
    dfa = ConcreteDFA([{}], {0})
    assert dfa.max_length(dfa.start) == 0
