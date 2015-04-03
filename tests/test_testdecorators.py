# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import time
import string
import inspect
from random import Random
from collections import namedtuple

import pytest
import hypothesis.settings as hs
import hypothesis.reporting as reporting
from hypothesis import given, assume
from hypothesis.core import _debugging_return_failing_example
from hypothesis.errors import Flaky, Unsatisfiable
from tests.common.utils import fails, fails_with, capture_out
from hypothesis.specifiers import just, one_of, sampled_from, \
    integers_from, floats_in_range, integers_in_range
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.internal.verifier import Verifier
from hypothesis.searchstrategy.numbers import IntStrategy


@given(int, int)
def test_int_addition_is_commutative(x, y):
    assert x + y == y + x


@fails
@given(text_type, text_type)
def test_str_addition_is_commutative(x, y):
    assert x + y == y + x


@fails
@given(binary_type, binary_type)
def test_bytes_addition_is_commutative(x, y):
    assert x + y == y + x


@given(int, int, int)
def test_int_addition_is_associative(x, y, z):
    assert x + (y + z) == (x + y) + z


@fails
@given(float, float, float)
def test_float_addition_is_associative(x, y, z):
    assert x + (y + z) == (x + y) + z


@given([int])
def test_reversing_preserves_integer_addition(xs):
    assert sum(xs) == sum(reversed(xs))


@fails
@given([float])
def test_reversing_does_not_preserve_float_addition(xs):
    assert sum(xs) == sum(reversed(xs))


def test_still_minimizes_on_non_assertion_failures():
    @given(int)
    def is_not_too_large(x):
        if x >= 10:
            raise ValueError('No, %s is just too large. Sorry' % x)

    with pytest.raises(ValueError) as exinfo:
        is_not_too_large()

    assert ' 10 ' in exinfo.value.args[0]


@given(int)
def test_integer_division_shrinks_positive_integers(n):
    assume(n > 0)
    assert n / 2 < n


class TestCases(object):

    @given(int)
    def test_abs_non_negative(self, x):
        assert abs(x) >= 0

    @fails
    @given(int)
    def test_int_is_always_negative(self, x):
        assert x < 0

    @fails
    @given(float, float)
    def test_float_addition_cancels(self, x, y):
        assert x + (y - x) == y


@fails
@given(int, name=str)
def test_can_be_given_keyword_args(x, name):
    assume(x > 0)
    assert len(name) < x


@fails_with(Unsatisfiable)
@given(int, settings=hs.Settings(timeout=0.1))
def test_slow_test_times_out(x):
    time.sleep(0.05)


# Cheap hack to make test functions which fail on their second invocation
calls = [0, 0, 0, 0]

timeout_settings = hs.Settings(timeout=0.2)


# The following tests exist to test that verifiers start their timeout
# from when the test first executes, not from when it is defined.
@fails
@given(int, settings=timeout_settings)
def test_slow_failing_test_1(x):
    time.sleep(0.05)
    assert not calls[0]
    calls[0] = 1


@fails
@given(int, settings=timeout_settings)
def test_slow_failing_test_2(x):
    time.sleep(0.05)
    assert not calls[1]
    calls[1] = 1


@fails
@given(int, verifier=Verifier(settings=timeout_settings))
def test_slow_failing_test_3(x):
    time.sleep(0.05)
    assert not calls[2]
    calls[2] = 1


@fails
@given(int, verifier=Verifier(settings=timeout_settings))
def test_slow_failing_test_4(x):
    time.sleep(0.05)
    assert not calls[3]
    calls[3] = 1


@fails
@given(one_of([int, str]), one_of([int, str]))
def test_one_of_produces_different_values(x, y):
    assert type(x) == type(y)


@given(just(42))
def test_is_the_answer(x):
    assert x == 42


@fails
@given(text_type, text_type)
def test_text_addition_is_not_commutative(x, y):
    assert x + y == y + x


@fails
@given(binary_type, binary_type)
def test_binary_addition_is_not_commutative(x, y):
    assert x + y == y + x


@given(integers_in_range(1, 10))
def test_integers_are_in_range(x):
    assert 1 <= x <= 10


@given(integers_from(100))
def test_integers_from_are_from(x):
    assert x >= 100


def test_does_not_catch_interrupt_during_falsify():
    calls = [0]

    @given(int)
    def flaky_base_exception(x):
        if not calls[0]:
            calls[0] = 1
            raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        flaky_base_exception()


def test_contains_the_test_function_name_in_the_exception_string():

    calls = [0]

    @given(int)
    def this_has_a_totally_unique_name(x):
        calls[0] += 1
        assume(False)

    with pytest.raises(Unsatisfiable) as e:
        this_has_a_totally_unique_name()
        print('Called %d times' % tuple(calls))

    assert this_has_a_totally_unique_name.__name__ in e.value.args[0]

    calls2 = [0]

    class Foo(object):

        @given(int)
        def this_has_a_unique_name_and_lives_on_a_class(self, x):
            calls2[0] += 1
            assume(False)

    with pytest.raises(Unsatisfiable) as e:
        Foo().this_has_a_unique_name_and_lives_on_a_class()
        print('Called %d times' % tuple(calls2))

    assert (
        Foo.this_has_a_unique_name_and_lives_on_a_class.__name__
    ) in e.value.args[0]


@given([int], int)
def test_removing_an_element_from_a_unique_list(xs, y):
    assume(len(set(xs)) == len(xs))

    try:
        xs.remove(y)
    except ValueError:
        pass

    assert y not in xs


@fails
@given([int], int)
def test_removing_an_element_from_a_non_unique_list(xs, y):
    assume(y in xs)
    xs.remove(y)
    assert y not in xs


def test_errors_even_if_does_not_error_on_final_call():
    @given(int)
    def rude(x):
        assert not any(
            t[3] == 'falsify'
            for t in inspect.getouterframes(inspect.currentframe())
        )

    with pytest.raises(Flaky):
        rude()


@given(set([sampled_from(list(range(10)))]))
def test_can_test_sets_sampled_from(xs):
    assert all(isinstance(x, int) for x in xs)
    assert all(0 <= x < 10 for x in xs)


mix = one_of((sampled_from([1, 2, 3]), str))


@fails
@given(mix, mix)
def test_can_mix_sampling_with_generating(x, y):
    assert type(x) == type(y)


@fails
@given(frozenset([int]))
def test_can_find_large_sum_frozenset(xs):
    assert sum(xs) < 100


def test_prints_on_failure_by_default():
    @given(int, int)
    def test_ints_are_sorted(balthazar, evans):
        assume(evans >= 0)
        assert balthazar <= evans
    with pytest.raises(AssertionError):
        with capture_out() as out:
            with reporting.with_reporter(reporting.default):
                test_ints_are_sorted()
    out = out.getvalue()
    lines = [l.strip() for l in out.split('\n')]
    assert (
        'Falsifying example: test_ints_are_sorted(balthazar=1, evans=0)'
        in lines)


def test_does_not_print_on_success():
    @given(int)
    def test_is_an_int(x):
        return True

    with capture_out() as out:
        test_is_an_int()
    out = out.getvalue()
    lines = [l.strip() for l in out.split('\n')]
    assert all(not l for l in lines)


@given(sampled_from([1]))
def test_can_sample_from_single_element(x):
    assert x == 1


@fails
@given([int])
def test_list_is_sorted(xs):
    assert sorted(xs) == xs


@fails
@given(floats_in_range(1.0, 2.0))
def test_is_an_endpoint(x):
    assert x == 1.0 or x == 2.0


def test_errors_when_given_varargs():
    with pytest.raises(TypeError) as e:
        @given(int)
        def has_varargs(*args):
            pass
    assert 'varargs' in e.value.args[0]


@pytest.mark.parametrize('t', [1, 10, 100, 1000])
@fails
@given(x=int)
def test_is_bounded(t, x):
    assert x < t


@given(x=bool)
def test_can_test_kwargs_only_methods(**kwargs):
    assert isinstance(kwargs['x'], bool)


def test_bare_given_errors():
    with pytest.raises(TypeError):
        given()


@fails_with(UnicodeEncodeError)
@given(text_type)
def test_is_ascii(x):
    x.encode('ascii')


@fails
@given(text_type)
def test_is_not_ascii(x):
    try:
        x.encode('ascii')
        assert False
    except UnicodeEncodeError:
        pass


@fails
@given(text_type)
def test_can_find_string_with_duplicates(s):
    assert len(set(s)) == len(s)


@fails
@given(text_type)
def test_has_ascii(x):
    if not x:
        return
    ascii_characters = (
        text_type('0123456789') + text_type(string.ascii_letters) +
        text_type(' \t\n')
    )
    assert any(c in ascii_characters for c in x)


first_call = True


@fails_with(Flaky)
@given(int)
def test_fails_only_once(x):
    global first_call
    if first_call:
        first_call = False
        assert False


class SpecialIntStrategy(IntStrategy):
    specifier = int

    def produce_parameter(self, random):
        return None

    def produce_template(self, context, parameter):
        return 1


@given([SpecialIntStrategy()])
def test_can_use_custom_strategies(xs):
    assert isinstance(xs, list)
    assert all(x == 1 for x in xs)


def test_uses_random():
    random = Random()
    initial = random.getstate()
    assert random.getstate() == initial

    @given(int, random=random)
    def test_foo(x):
        pass
    test_foo()
    assert random.getstate() != initial


def test_does_not_accept_random_if_derandomize():
    with pytest.raises(ValueError):
        @given(int, settings=hs.Settings(derandomize=True), random=Random())
        def test_blah(x):
            pass


def test_can_derandomize():
    @fails
    @given(int, settings=hs.Settings(derandomize=True))
    def test_blah(x):
        assert x > 0

    test_blah()


def test_can_run_without_database():
    @given(int, settings=hs.Settings(database=None))
    def test_blah(x):
        assert False
    with pytest.raises(AssertionError):
        test_blah()


@given(int)
def test_can_call_an_argument_f(f):
    # See issue https://github.com/DRMacIver/hypothesis/issues/38 for details
    pass


def test_can_abuse_given_into_returning_value():
    @given(int)
    def test_is_negative(x):
        assert x < 0

    with _debugging_return_failing_example.with_value(True):
        assert test_is_negative() == ((), {'x': 0})


Litter = namedtuple('Litter', ('kitten1', 'kitten2'))


@given(Litter(int, int))
def test_named_tuples_are_of_right_type(litter):
    assert isinstance(litter, Litter)
