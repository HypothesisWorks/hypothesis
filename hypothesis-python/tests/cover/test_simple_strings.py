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

from random import Random

from hypothesis import given
from hypothesis.strategies import binary, characters, text, tuples
from tests.common.debug import minimal
from tests.common.utils import checks_deprecated_behaviour, fails_with


def test_can_minimize_up_to_zero():
    s = minimal(text(), lambda x: any(lambda t: t <= u"0" for t in x))
    assert s == u"0"


def test_minimizes_towards_ascii_zero():
    s = minimal(text(), lambda x: any(t < u"0" for t in x))
    assert s == chr(ord(u"0") - 1)


def test_can_handle_large_codepoints():
    s = minimal(text(), lambda x: x >= u"☃")
    assert s == u"☃"


def test_can_find_mixed_ascii_and_non_ascii_strings():
    s = minimal(
        text(), lambda x: (any(t >= u"☃" for t in x) and any(ord(t) <= 127 for t in x))
    )
    assert len(s) == 2
    assert sorted(s) == [u"0", u"☃"]


def test_will_find_ascii_examples_given_the_chance():
    s = minimal(
        tuples(text(max_size=1), text(max_size=1)), lambda x: x[0] and (x[0] < x[1])
    )
    assert ord(s[1]) == ord(s[0]) + 1
    assert u"0" in s


def test_finds_single_element_strings():
    assert minimal(text(), bool, random=Random(4)) == u"0"


@fails_with(AssertionError)
@given(binary())
def test_binary_generates_large_examples(x):
    assert len(x) <= 20


@given(binary(max_size=5))
def test_binary_respects_max_size(x):
    assert len(x) <= 5


def test_does_not_simplify_into_surrogates():
    f = minimal(text(), lambda x: x >= u"\udfff")
    assert f == u"\ue000"

    size = 5

    f = minimal(text(min_size=size), lambda x: sum(t >= u"\udfff" for t in x) >= size)
    assert f == u"\ue000" * size


@given(text(alphabet=[u"a", u"b"]))
def test_respects_alphabet_if_list(xs):
    assert set(xs).issubset(set(u"ab"))


@given(text(alphabet=u"cdef"))
def test_respects_alphabet_if_string(xs):
    assert set(xs).issubset(set(u"cdef"))


@given(text())
def test_can_encode_as_utf8(s):
    s.encode("utf-8")


@given(text(characters(blacklist_characters=u"\n")))
def test_can_blacklist_newlines(s):
    assert u"\n" not in s


@given(text(characters(blacklist_categories=("Cc", "Cs"))))
def test_can_exclude_newlines_by_category(s):
    assert u"\n" not in s


@given(text(characters(max_codepoint=127)))
def test_can_restrict_to_ascii_only(s):
    s.encode("ascii")


def test_fixed_size_bytes_just_draw_bytes():
    from hypothesis.internal.conjecture.data import ConjectureData

    x = ConjectureData.for_buffer(b"foo")
    assert x.draw(binary(min_size=3, max_size=3)) == b"foo"


@given(text(max_size=10 ** 6))
def test_can_set_max_size_large(s):
    pass


@checks_deprecated_behaviour
def test_explicit_alphabet_None_is_deprecated():
    text(alphabet=None).example()
