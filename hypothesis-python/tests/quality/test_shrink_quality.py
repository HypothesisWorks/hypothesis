# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from collections import Counter, OrderedDict, namedtuple
from fractions import Fraction
from functools import reduce

import pytest

import hypothesis.strategies as st
from hypothesis import HealthCheck, assume, given, settings
from hypothesis.strategies import (
    booleans,
    builds,
    dictionaries,
    fixed_dictionaries,
    fractions,
    frozensets,
    integers,
    just,
    lists,
    none,
    sampled_from,
    sets,
    text,
    tuples,
)

from tests.common.debug import minimal
from tests.common.utils import flaky


def test_integers_from_minimizes_leftwards():
    assert minimal(integers(min_value=101)) == 101


def test_minimize_bounded_integers_to_zero():
    assert minimal(integers(-10, 10)) == 0


def test_minimize_bounded_integers_to_positive():
    zero = 0

    def not_zero(x):
        return x != zero

    assert minimal(integers(-10, 10).filter(not_zero)) == 1


def test_minimal_fractions_1():
    assert minimal(fractions()) == Fraction(0)


def test_minimal_fractions_2():
    assert minimal(fractions(), lambda x: x >= 1) == Fraction(1)


def test_minimal_fractions_3():
    assert minimal(lists(fractions()), lambda s: len(s) >= 5) == [Fraction(0)] * 5


def test_minimize_string_to_empty():
    assert minimal(text()) == ""


def test_minimize_one_of():
    for _ in range(100):
        assert minimal(integers() | text() | booleans()) in (0, "", False)


def test_minimize_mixed_list():
    mixed = minimal(lists(integers() | text()), lambda x: len(x) >= 10)
    assert set(mixed).issubset({0, ""})


def test_minimize_longer_string():
    assert minimal(text(), lambda x: len(x) >= 10) == "0" * 10


def test_minimize_longer_list_of_strings():
    assert minimal(lists(text()), lambda x: len(x) >= 10) == [""] * 10


def test_minimize_3_set():
    assert minimal(sets(integers()), lambda x: len(x) >= 3) in ({0, 1, 2}, {-1, 0, 1})


def test_minimize_3_set_of_tuples():
    assert minimal(sets(tuples(integers())), lambda x: len(x) >= 2) == {(0,), (1,)}


def test_minimize_sets_of_sets():
    elements = integers(1, 100)
    size = 8
    set_of_sets = minimal(sets(frozensets(elements), min_size=size))
    assert frozenset() in set_of_sets
    assert len(set_of_sets) == size
    for s in set_of_sets:
        if len(s) > 1:
            assert any(s != t and t.issubset(s) for t in set_of_sets)


def test_minimize_sets_sampled_from():
    assert minimal(st.sets(st.sampled_from(range(10)), min_size=3)) == {0, 1, 2}


def test_can_simplify_flatmap_with_bounded_left_hand_size():
    assert (
        minimal(booleans().flatmap(lambda x: lists(just(x))), lambda x: len(x) >= 10)
        == [False] * 10
    )


def test_can_simplify_across_flatmap_of_just():
    assert minimal(integers().flatmap(just)) == 0


def test_can_simplify_on_right_hand_strategy_of_flatmap():
    assert minimal(integers().flatmap(lambda x: lists(just(x)))) == []


@flaky(min_passes=5, max_runs=5)
def test_can_ignore_left_hand_side_of_flatmap():
    assert (
        minimal(integers().flatmap(lambda x: lists(integers())), lambda x: len(x) >= 10)
        == [0] * 10
    )


def test_can_simplify_on_both_sides_of_flatmap():
    assert (
        minimal(integers().flatmap(lambda x: lists(just(x))), lambda x: len(x) >= 10)
        == [0] * 10
    )


def test_flatmap_rectangles():
    lengths = integers(min_value=0, max_value=10)

    def lists_of_length(n):
        return lists(sampled_from("ab"), min_size=n, max_size=n)

    xs = minimal(
        lengths.flatmap(lambda w: lists(lists_of_length(w))),
        lambda x: ["a", "b"] in x,
        settings=settings(database=None, max_examples=2000),
    )
    assert xs == [["a", "b"]]


@flaky(min_passes=5, max_runs=5)
@pytest.mark.parametrize("dict_class", [dict, OrderedDict])
def test_dictionary(dict_class):
    assert (
        minimal(dictionaries(keys=integers(), values=text(), dict_class=dict_class))
        == dict_class()
    )

    x = minimal(
        dictionaries(keys=integers(), values=text(), dict_class=dict_class),
        lambda t: len(t) >= 3,
    )
    assert isinstance(x, dict_class)
    assert set(x.values()) == {""}
    for k in x:
        if k < 0:
            assert k + 1 in x
        if k > 0:
            assert k - 1 in x


def test_minimize_single_element_in_silly_large_int_range():
    assert minimal(integers(-(2**256), 2**256), lambda x: x >= -(2**255)) == 0


def test_minimize_multiple_elements_in_silly_large_int_range():
    actual = minimal(
        lists(integers(-(2**256), 2**256)),
        lambda x: len(x) >= 20,
        settings(max_examples=10_000),
    )
    assert actual == [0] * 20


def test_minimize_multiple_elements_in_silly_large_int_range_min_is_not_dupe():
    target = list(range(20))

    actual = minimal(
        lists(integers(0, 2**256)),
        lambda x: (assume(len(x) >= 20) and all(x[i] >= target[i] for i in target)),
    )
    assert actual == target


def test_find_large_union_list():
    size = 10

    def large_mostly_non_overlapping(xs):
        union = reduce(set.union, xs)
        return len(union) >= size

    result = minimal(
        lists(sets(integers(), min_size=1), min_size=1),
        large_mostly_non_overlapping,
    )
    assert len(result) == 1
    union = reduce(set.union, result)
    assert len(union) == size
    assert max(union) == min(union) + len(union) - 1


@pytest.mark.parametrize("n", [0, 1, 10, 100, 1000])
@pytest.mark.parametrize(
    "seed", [13878544811291720918, 15832355027548327468, 12901656430307478246]
)
def test_containment(n, seed):
    iv = minimal(
        tuples(lists(integers()), integers()),
        lambda x: x[1] in x[0] and x[1] >= n,
    )
    assert iv == ([n], n)


def test_duplicate_containment():
    ls, i = minimal(
        tuples(lists(integers()), integers()),
        lambda s: s[0].count(s[1]) > 1,
    )
    assert ls == [0, 0]
    assert i == 0


@pytest.mark.parametrize("seed", [11, 28, 37])
def test_reordering_bytes(seed):
    ls = minimal(lists(integers()), lambda x: sum(x) >= 10 and len(x) >= 3)
    assert ls == sorted(ls)


def test_minimize_long_list():
    assert (
        minimal(lists(booleans(), min_size=50), lambda x: len(x) >= 70) == [False] * 70
    )


def test_minimize_list_of_longish_lists():
    size = 5
    xs = minimal(
        lists(lists(booleans())),
        lambda x: len([t for t in x if any(t) and len(t) >= 2]) >= size,
    )
    assert len(xs) == size
    for x in xs:
        assert x == [False, True]


def test_minimize_list_of_fairly_non_unique_ints():
    xs = minimal(lists(integers()), lambda x: len(set(x)) < len(x))
    assert len(xs) == 2


def test_list_with_complex_sorting_structure():
    xs = minimal(
        lists(lists(booleans())),
        lambda x: [list(reversed(t)) for t in x] > x and len(x) > 3,
    )
    assert len(xs) == 4


def test_list_with_wide_gap():
    xs = minimal(lists(integers()), lambda x: x and (max(x) > min(x) + 10 > 0))
    assert len(xs) == 2
    xs.sort()
    assert xs[1] == 11 + xs[0]


def test_minimize_namedtuple():
    T = namedtuple("T", ("a", "b"))
    tab = minimal(builds(T, integers(), integers()), lambda x: x.a < x.b)
    assert tab.b == tab.a + 1


def test_minimize_dict():
    tab = minimal(
        fixed_dictionaries({"a": booleans(), "b": booleans()}),
        lambda x: x["a"] or x["b"],
    )
    assert not (tab["a"] and tab["b"])


def test_minimize_list_of_sets():
    assert minimal(
        lists(sets(booleans())), lambda x: len(list(filter(None, x))) >= 3
    ) == ([{False}] * 3)


def test_minimize_list_of_lists():
    assert minimal(
        lists(lists(integers())), lambda x: len(list(filter(None, x))) >= 3
    ) == ([[0]] * 3)


def test_minimize_list_of_tuples():
    xs = minimal(lists(tuples(integers(), integers())), lambda x: len(x) >= 2)
    assert xs == [(0, 0), (0, 0)]


def test_minimize_multi_key_dicts():
    assert minimal(dictionaries(keys=booleans(), values=booleans()), bool) == {
        False: False
    }


def test_multiple_empty_lists_are_independent():
    x = minimal(lists(lists(none(), max_size=0)), lambda t: len(t) >= 2)
    u, v = x
    assert u is not v


def test_can_find_sets_unique_by_incomplete_data():
    size = 5
    ls = minimal(
        lists(tuples(integers(), integers()), unique_by=max), lambda x: len(x) >= size
    )
    assert len(ls) == size
    values = sorted(map(max, ls))
    assert values[-1] - values[0] == size - 1
    for u, _ in ls:
        assert u <= 0


@pytest.mark.parametrize("n", range(10))
def test_lists_forced_near_top(n):
    assert minimal(
        lists(integers(), min_size=n, max_size=n + 2), lambda t: len(t) == n + 2
    ) == [0] * (n + 2)


def test_sum_of_pair_int():
    assert minimal(
        tuples(integers(0, 1000), integers(0, 1000)), lambda x: sum(x) > 1000
    ) == (1, 1000)


def test_sum_of_pair_float():
    assert minimal(
        tuples(st.floats(0, 1000), st.floats(0, 1000)), lambda x: sum(x) > 1000
    ) == (1.0, 1000.0)


def test_sum_of_pair_mixed():
    # check both orderings
    assert minimal(
        tuples(st.floats(0, 1000), st.integers(0, 1000)), lambda x: sum(x) > 1000
    ) == (1.0, 1000)
    assert minimal(
        tuples(st.integers(0, 1000), st.floats(0, 1000)), lambda x: sum(x) > 1000
    ) == (1, 1000.0)


def test_sum_of_pair_separated_int():
    @st.composite
    def separated_sum(draw):
        n1 = draw(st.integers(0, 1000))
        draw(st.text())
        draw(st.booleans())
        draw(st.integers())
        n2 = draw(st.integers(0, 1000))
        return (n1, n2)

    assert minimal(separated_sum(), lambda x: sum(x) > 1000) == (1, 1000)


def test_sum_of_pair_separated_float():
    @st.composite
    def separated_sum(draw):
        f1 = draw(st.floats(0, 1000))
        draw(st.text())
        draw(st.booleans())
        draw(st.integers())
        f2 = draw(st.floats(0, 1000))
        return (f1, f2)

    assert minimal(separated_sum(), lambda x: sum(x) > 1000) == (1, 1000)


def test_calculator_benchmark():
    """This test comes from
    https://github.com/jlink/shrinking-challenge/blob/main/challenges/calculator.md,
    which is originally from Pike, Lee. "SmartCheck: automatic and efficient
    counterexample reduction and generalization."
    Proceedings of the 2014 ACM SIGPLAN symposium on Haskell. 2014.
    """

    expression = st.deferred(
        lambda: st.one_of(
            st.integers(),
            st.tuples(st.just("+"), expression, expression),
            st.tuples(st.just("/"), expression, expression),
        )
    )

    def div_subterms(e):
        if isinstance(e, int):
            return True
        if e[0] == "/" and e[-1] == 0:
            return False
        return div_subterms(e[1]) and div_subterms(e[2])

    def evaluate(e):
        if isinstance(e, int):
            return e
        elif e[0] == "+":
            return evaluate(e[1]) + evaluate(e[2])
        else:
            assert e[0] == "/"
            return evaluate(e[1]) // evaluate(e[2])

    def is_failing(e):
        assume(div_subterms(e))
        try:
            evaluate(e)
            return False
        except ZeroDivisionError:
            return True

    x = minimal(expression, is_failing)

    assert x == ("/", 0, ("+", 0, 0))


def test_one_of_slip():
    assert minimal(st.integers(101, 200) | st.integers(0, 100)) == 101


# this limit is only to avoid Unsatisfiable when searching for an initial
# counterexample in minimal, as we may generate a very large magnitude n.
@given(st.integers(-(2**32), 2**32))
@settings(max_examples=3, suppress_health_check=[HealthCheck.nested_given])
def test_perfectly_shrinks_integers(n):
    if n >= 0:
        assert minimal(st.integers(), lambda x: x >= n) == n
    else:
        assert minimal(st.integers(), lambda x: x <= n) == n


@given(st.integers(0, 20))
@settings(suppress_health_check=[HealthCheck.nested_given])
def test_lowering_together_positive(gap):
    s = st.tuples(st.integers(0, 20), st.integers(0, 20))
    assert minimal(s, lambda x: x[0] + gap == x[1]) == (0, gap)


@given(st.integers(-20, 0))
@settings(suppress_health_check=[HealthCheck.nested_given])
def test_lowering_together_negative(gap):
    s = st.tuples(st.integers(-20, 0), st.integers(-20, 0))
    assert minimal(s, lambda x: x[0] + gap == x[1]) == (0, gap)


@given(st.integers(-10, 10))
@settings(suppress_health_check=[HealthCheck.nested_given])
def test_lowering_together_mixed(gap):
    s = st.tuples(st.integers(-10, 10), st.integers(-10, 10))
    assert minimal(s, lambda x: x[0] + gap == x[1]) == (0, gap)


@given(st.integers(-10, 10))
@settings(suppress_health_check=[HealthCheck.nested_given])
def test_lowering_together_with_gap(gap):
    s = st.tuples(st.integers(-10, 10), st.text(), st.floats(), st.integers(-10, 10))
    assert minimal(s, lambda x: x[0] + gap == x[3]) == (0, "", 0.0, gap)


def test_run_length_encoding():
    # extracted from https://github.com/HypothesisWorks/hypothesis/issues/4286,
    # as well as our docs

    def decode(table: list[tuple[int, str]]) -> str:
        out = ""
        for count, char in table:
            out += count * char
        return out

    def encode(s: str) -> list[tuple[int, str]]:
        count = 1
        prev = ""
        out = []

        if not s:
            return []

        for char in s:
            if char != prev:
                if prev:
                    entry = (count, prev)
                    out.append(entry)
                # BUG:
                # count = 1
                prev = char
            else:
                count += 1

        entry = (count, char)
        out.append(entry)
        return out

    assert minimal(st.text(), lambda s: decode(encode(s)) != s) == "001"


def test_minimize_duplicated_characters_within_a_choice():
    # look for strings which have at least 3 of the same character, and also at
    # least two different characters (to avoid the trivial shrink of replacing
    # everything with "0" from working).

    # we should test this for st.binary too, but it's difficult to get it
    # to satisfy this precondition in the first place (probably worth improving
    # our generation here to duplicate binary elements in generate_mutations_from)
    assert (
        minimal(
            st.text(min_size=1),
            lambda v: Counter(v).most_common()[0][1] > 2 and len(set(v)) > 1,
        )
        == "0001"
    )


def test_nasty_string_shrinks():
    # failures found via NASTY_STRINGS should shrink like normal
    assert (
        minimal(st.text(), lambda s: "𝕿𝖍𝖊" in s, settings=settings(max_examples=10000))
        == "𝕿𝖍𝖊"
    )
