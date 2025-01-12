# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import given
from hypothesis.strategies import binary, characters, text, tuples

from tests.common.debug import minimal


def test_can_minimize_up_to_zero():
    s = minimal(text(), lambda x: any(lambda t: t <= "0" for t in x))
    assert s == "0"


def test_minimizes_towards_ascii_zero():
    s = minimal(text(), lambda x: any(t < "0" for t in x))
    assert s == chr(ord("0") - 1)


def test_can_handle_large_codepoints():
    s = minimal(text(), lambda x: x >= "☃")
    assert s == "☃"


def test_can_find_mixed_ascii_and_non_ascii_strings():
    s = minimal(
        text(), lambda x: (any(t >= "☃" for t in x) and any(ord(t) <= 127 for t in x))
    )
    assert len(s) == 2
    assert sorted(s) == ["0", "☃"]


def test_will_find_ascii_examples_given_the_chance():
    s = minimal(
        tuples(text(max_size=1), text(max_size=1)), lambda x: x[0] and (x[0] < x[1])
    )
    assert ord(s[1]) == ord(s[0]) + 1
    assert "0" in s


def test_minimisation_consistent_with_characters():
    s = minimal(text("FEDCBA", min_size=3))
    assert s == "AAA"


def test_finds_single_element_strings():
    assert minimal(text(), bool) == "0"


@given(binary(max_size=5))
def test_binary_respects_max_size(x):
    assert len(x) <= 5


def test_does_not_simplify_into_surrogates():
    f = minimal(text(), lambda x: x >= "\udfff")
    assert f == "\ue000"

    size = 5

    f = minimal(text(min_size=size), lambda x: sum(t >= "\udfff" for t in x) >= size)
    assert f == "\ue000" * size


@given(text(alphabet=["a", "b"]))
def test_respects_alphabet_if_list(xs):
    assert set(xs).issubset(set("ab"))


@given(text(alphabet="cdef"))
def test_respects_alphabet_if_string(xs):
    assert set(xs).issubset(set("cdef"))


@given(text())
def test_can_encode_as_utf8(s):
    s.encode()


@given(text(characters(exclude_characters="\n")))
def test_can_blacklist_newlines(s):
    assert "\n" not in s


@given(text(characters(exclude_categories=("Cc", "Cs"))))
def test_can_exclude_newlines_by_category(s):
    assert "\n" not in s


@given(text(characters(max_codepoint=127)))
def test_can_restrict_to_ascii_only(s):
    s.encode("ascii")


def test_fixed_size_bytes_just_draw_bytes():
    from hypothesis.internal.conjecture.data import ConjectureData

    x = ConjectureData.for_choices([b"foo"])
    assert x.draw(binary(min_size=3, max_size=3)) == b"foo"


@given(text(max_size=10**6))
def test_can_set_max_size_large(s):
    pass
