from __future__ import division, print_function, absolute_import

import hypothesis.strategies as st
from hypothesis import note, given, assume
from hypothesis.internal.chooser import AliasChooser


@given(
    st.lists(st.integers(min_value=0), min_size=2).filter(
        lambda x: sum(x) > 0),
    st.randoms()
)
def test_can_choose_from_a_weighted_set(weights, rnd):
    chooser = AliasChooser(weights)
    i = chooser.choose(rnd)
    note(repr(weights))
    note(repr(i))
    assert 0 <= i < len(weights)
    assert weights[i] != 0


def estimate_chooser(chooser, rnd):
    r = [0] * chooser.size
    for _ in range(100 * (chooser.size + 1)):
        r[chooser.choose(rnd)] += 1
    return r


@given(
    st.lists(st.integers(min_value=0, max_value=10), min_size=2).filter(
        lambda x: sum(x) > 0),
    st.randoms()
)
def test_chooser_covers_everything(weights, rnd):
    chooser = AliasChooser(weights)
    estimate = estimate_chooser(chooser, rnd)
    for e, w in zip(estimate, weights):
        assert (e == 0) == (w == 0)


@given(
    st.lists(st.integers(min_value=0), min_size=2).filter(
        lambda x: sum(x) > 0),
    st.randoms()
)
def test_gross_bias_is_noticed(weights, rnd):
    assume(max(weights) > 2 * min(weights))
    chooser = AliasChooser(weights)
    estimate = estimate_chooser(chooser, rnd)
    i = max(range(chooser.size), key=weights.__getitem__)
    j = min(range(chooser.size), key=weights.__getitem__)
    assert estimate[i] > estimate[j]
