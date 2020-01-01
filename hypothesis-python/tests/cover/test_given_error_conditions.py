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

import pytest

from hypothesis import assume, given, infer, reject, settings
from hypothesis.errors import InvalidArgument, Unsatisfiable
from hypothesis.strategies import booleans, integers
from tests.common.utils import fails_with


def test_raises_unsatisfiable_if_all_false_in_finite_set():
    @given(booleans())
    def test_assume_false(x):
        reject()

    with pytest.raises(Unsatisfiable):
        test_assume_false()


def test_does_not_raise_unsatisfiable_if_some_false_in_finite_set():
    @given(booleans())
    def test_assume_x(x):
        assume(x)

    test_assume_x()


def test_error_if_has_no_hints():
    @given(a=infer)
    def inner(a):
        pass

    with pytest.raises(InvalidArgument):
        inner()


def test_error_if_infer_is_posarg():
    @given(infer)
    def inner(ex):
        pass

    with pytest.raises(InvalidArgument):
        inner()


def test_given_twice_is_an_error():
    @settings(deadline=None)
    @given(booleans())
    @given(integers())
    def inner(a, b):
        pass

    with pytest.raises(InvalidArgument):
        inner()


@fails_with(InvalidArgument)
def test_given_is_not_a_class_decorator():
    @given(integers())
    class test_given_is_not_a_class_decorator:
        def __init__(self, i):
            pass
