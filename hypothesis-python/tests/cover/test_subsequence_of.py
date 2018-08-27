# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import hypothesis.strategies as st
from hypothesis import given
from tests.common.debug import assert_no_examples


def test_subsequence_of_empty():
    sub_seq_strat = st.lists(st.none(), max_size=0)
    # assert strat.is_empty  # See #1517
    assert_no_examples(sub_seq_strat)


@given(st.data(), st.lists(st.integers()))
def test_subsequence_sizing(data, seq):
    sub_seq_strat = st.subsequence_of(seq)
    sub_seq = data.draw(sub_seq_strat)

    assert isinstance(sub_seq, list)
    assert len(sub_seq) <= len(seq)


@given(st.data(), st.lists(st.integers()))
def test_subsequence_only_original_elements(data, seq):
    sub_seq_strat = st.subsequence_of(seq)
    sub_seq = data.draw(sub_seq_strat)

    assert isinstance(sub_seq, list)
    assert len(sub_seq) <= len(seq)


@given(st.data(), st.lists(st.integers()))
def test_subsequence_elements_not_over_drawn(data, seq):
    sub_seq_strat = st.subsequence_of(seq)
    sub_seq = data.draw(sub_seq_strat)

    assert not (set(sub_seq) - set(seq))


@given(st.data(), st.lists(st.integers()))
def test_subsequence_original_elements_not_over_produced(data, seq):
    sub_seq_strat = st.subsequence_of(seq)
    sub_seq = data.draw(sub_seq_strat)

    # Per unique item, check that they don't occur in the subsequence
    # more times that they appear in the source.
    for item in set(sub_seq):
        assert sub_seq.count(item) <= seq.count(item)


@given(st.data(), st.lists(st.integers()))
def test_subsequence_max_size_constraint(data, seq):
    # Make a maximum length constraint of the subsequence, that's no
    # longer than the main sequence too.
    max_size_strat = st.integers(min_value=0, max_value=len(seq))
    max_size = data.draw(max_size_strat)

    sub_seq_strat = st.subsequence_of(seq, max_size=max_size)
    sub_seq = data.draw(sub_seq_strat)

    assert len(sub_seq) <= max_size


@given(st.data(), st.lists(st.integers()))
def test_subsequence_min_size_constraint(data, seq):
    # Make a maximum length constraint of the subsequence, that's no
    # longer than the main sequence too.
    min_size_strat = st.integers(min_value=0, max_value=len(seq))
    min_size = data.draw(min_size_strat)

    sub_seq_strat = st.subsequence_of(seq, min_size=min_size)
    sub_seq = data.draw(sub_seq_strat)

    assert len(sub_seq) >= min_size


@given(st.data(), st.lists(st.integers()))
def test_subsequence_min_max_size_constraint(data, seq):
    # Make a maximum length constraint of the subsequence, that's no
    # longer than the main sequence too.
    min_size_strat = st.integers(min_value=0, max_value=len(seq))
    min_size = data.draw(min_size_strat)

    max_size_strat = st.integers(min_value=min_size, max_value=len(seq))
    max_size = data.draw(max_size_strat)

    sub_seq_strat = st.subsequence_of(seq, min_size=min_size, max_size=max_size)
    sub_seq = data.draw(sub_seq_strat)

    assert min_size <= len(sub_seq) <= max_size
