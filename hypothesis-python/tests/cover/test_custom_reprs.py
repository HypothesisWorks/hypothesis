# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import re

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.strategies._internal.lazy import unwrap_strategies


def test_includes_non_default_args_in_repr():
    assert repr(st.integers()) == "integers()"
    assert repr(st.integers(min_value=1)) == "integers(min_value=1)"


def test_sampled_repr_leaves_range_as_range():
    huge = 10**100
    assert repr(st.sampled_from(range(huge))) == f"sampled_from(range(0, {huge}))"


def hi(there, stuff):
    return there


def test_supports_positional_and_keyword_args_in_builds():
    assert (
        repr(st.builds(hi, st.integers(), there=st.booleans()))
        == "builds(hi, integers(), there=booleans())"
    )


def test_preserves_sequence_type_of_argument():
    assert repr(st.sampled_from([0, 1])) == "sampled_from([0, 1])"
    assert repr(st.sampled_from((0, 1))) == "sampled_from((0, 1))"


class IHaveABadRepr:
    def __repr__(self):
        raise ValueError("Oh no!")


def test_errors_are_deferred_until_repr_is_calculated():
    s = (
        st.builds(
            lambda x, y: 1,
            st.just(IHaveABadRepr()),
            y=st.one_of(st.sampled_from((IHaveABadRepr(),)), st.just(IHaveABadRepr())),
        )
        .map(lambda t: t)
        .filter(lambda t: True)
        .flatmap(lambda t: st.just(IHaveABadRepr()))
    )

    with pytest.raises(ValueError):
        repr(s)


@given(st.iterables(st.integers()))
def test_iterables_repr_is_useful(it):
    # fairly hard-coded but useful; also ensures _values are inexhaustible
    assert repr(it) == f"iter({it._values!r})"


class Foo:
    def __init__(self, x: int) -> None:
        self.x = x


class Bar(Foo):
    pass


def test_reprs_as_created():
    @given(foo=st.builds(Foo), bar=st.from_type(Bar), baz=st.none().map(Foo))
    @settings(print_blob=False, max_examples=10_000, derandomize=True)
    def inner(foo, bar, baz):
        assert baz.x is None
        assert foo.x <= 0 or bar.x >= 0

    with pytest.raises(AssertionError) as err:
        inner()
    expected = """
Falsifying example: inner(
    foo=Foo(x=1),
    bar=Bar(x=-1),
    baz=Foo(None),
)
"""
    assert "\n".join(err.value.__notes__).strip() == expected.strip()


def test_reprs_as_created_interactive():
    @given(st.data())
    @settings(print_blob=False, max_examples=10_000)
    def inner(data):
        bar = data.draw(st.builds(Bar, st.just(10)))
        assert not bar.x

    with pytest.raises(AssertionError) as err:
        inner()
    expected = """
Falsifying example: inner(
    data=data(...),
)
Draw 1: Bar(10)
"""
    assert "\n".join(err.value.__notes__).strip() == expected.strip()


CONSTANT_FOO = Foo(None)


def some_foo(*_):
    return CONSTANT_FOO


def test_as_created_reprs_fallback_for_distinct_calls_same_obj():
    # If we have *different* calls which return the *same* object, we skip our
    # nice repr because it's unclear which one we should use.
    @given(st.builds(some_foo), st.builds(some_foo, st.none()))
    @settings(print_blob=False, max_examples=10_000)
    def inner(a, b):
        assert a is not b

    with pytest.raises(AssertionError) as err:
        inner()
    expected_re = r"""
Falsifying example: inner\(
    a=<.*Foo object at 0x[0-9A-Fa-f]+>,
    b=<.*Foo object at 0x[0-9A-Fa-f]+>,
\)
""".strip()
    got = "\n".join(err.value.__notes__).strip()
    assert re.fullmatch(expected_re, got), got


def test_reprs_as_created_consistent_calls_despite_indentation():
    aas = "a" * 60
    strat = st.builds(some_foo, st.just(aas))

    # If we have multiple calls which return the same object, we can print their
    # nice repr even if varying indentation means that they'll come out different!
    @given(strat, st.builds(Bar, strat))
    @settings(print_blob=False, max_examples=10_000)
    def inner(a, b):
        assert a == b

    with pytest.raises(AssertionError) as err:
        inner()
    expected = f"""
Falsifying example: inner(
    a=some_foo({aas!r}),
    b=Bar(
        some_foo(
            {aas!r},
        ),
    ),
)
"""
    assert "\n".join(err.value.__notes__).strip() == expected.strip()


@pytest.mark.parametrize(
    "strategy, expected_repr",
    [
        (st.characters(), "characters()"),
        (st.characters(codec="utf-8"), "characters(codec='utf-8')"),
        (st.characters(min_codepoint=65), "characters(min_codepoint=65)"),
        (st.characters(max_codepoint=127), "characters(max_codepoint=127)"),
        (st.characters(categories=["Lu", "Ll"]), "characters(categories=('Lu', 'Ll'))"),
        (
            st.characters(exclude_characters="abc"),
            "characters(exclude_characters='abc')",
        ),
        (
            st.characters(min_codepoint=65, max_codepoint=90),
            "characters(min_codepoint=65, max_codepoint=90)",
        ),
        (
            st.characters(codec="ascii", min_codepoint=32, max_codepoint=126),
            "characters(min_codepoint=32, max_codepoint=126)",
        ),
        (
            st.characters(categories=["Lu"], exclude_characters="AZ"),
            "characters(categories=('Lu',), exclude_characters='AZ')",
        ),
    ],
)
def test_characters_repr(strategy, expected_repr):
    assert repr(unwrap_strategies(strategy)) == expected_repr
