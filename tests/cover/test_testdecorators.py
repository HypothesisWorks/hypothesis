# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

import time
import functools
import threading
from collections import namedtuple

import hypothesis.reporting as reporting
from hypothesis import note, seed, given, assume, reject, settings, \
    Verbosity
from hypothesis.errors import Unsatisfiable
from tests.common.utils import fails, raises, fails_with, capture_out
from hypothesis.strategies import just, sets, text, lists, binary, \
    builds, floats, one_of, booleans, integers, frozensets, sampled_from


@given(integers(), integers())
def test_int_addition_is_commutative(x, y):
    assert x + y == y + x


@fails
@given(text(), text())
def test_str_addition_is_commutative(x, y):
    assert x + y == y + x


@fails
@given(binary(), binary())
def test_bytes_addition_is_commutative(x, y):
    assert x + y == y + x


@given(integers(), integers(), integers())
def test_int_addition_is_associative(x, y, z):
    assert x + (y + z) == (x + y) + z


@fails
@given(floats(), floats(), floats())
@settings(max_examples=2000,)
def test_float_addition_is_associative(x, y, z):
    assert x + (y + z) == (x + y) + z


@given(lists(integers()))
def test_reversing_preserves_integer_addition(xs):
    assert sum(xs) == sum(reversed(xs))


def test_still_minimizes_on_non_assertion_failures():
    @settings(max_examples=50)
    @given(integers())
    def is_not_too_large(x):
        if x >= 10:
            raise ValueError('No, %s is just too large. Sorry' % x)

    with raises(ValueError) as exinfo:
        is_not_too_large()

    assert ' 10 ' in exinfo.value.args[0]


@given(integers())
def test_integer_division_shrinks_positive_integers(n):
    assume(n > 0)
    assert n / 2 < n


class TestCases(object):

    @given(integers())
    def test_abs_non_negative(self, x):
        assert abs(x) >= 0
        assert isinstance(self, TestCases)

    @given(x=integers())
    def test_abs_non_negative_varargs(self, x, *args):
        assert abs(x) >= 0
        assert isinstance(self, TestCases)

    @given(x=integers())
    def test_abs_non_negative_varargs_kwargs(self, *args, **kw):
        assert abs(kw['x']) >= 0
        assert isinstance(self, TestCases)

    @given(x=integers())
    def test_abs_non_negative_varargs_kwargs_only(*args, **kw):
        assert abs(kw['x']) >= 0
        assert isinstance(args[0], TestCases)

    @fails
    @given(integers())
    def test_int_is_always_negative(self, x):
        assert x < 0

    @fails
    @given(floats(), floats())
    def test_float_addition_cancels(self, x, y):
        assert x + (y - x) == y


@fails
@given(x=integers(min_value=0, max_value=3), name=text())
def test_can_be_given_keyword_args(x, name):
    assume(x > 0)
    assert len(name) < x


@fails_with(Unsatisfiable)
@settings(timeout=0.1)
@given(integers())
def test_slow_test_times_out(x):
    time.sleep(0.05)


# Cheap hack to make test functions which fail on their second invocation
calls = [0, 0, 0, 0]

timeout_settings = settings(timeout=0.2, min_satisfying_examples=2)


# The following tests exist to test that verifiers start their timeout
# from when the test first executes, not from when it is defined.
@fails
@given(integers())
@timeout_settings
def test_slow_failing_test_1(x):
    time.sleep(0.05)
    assert not calls[0]
    calls[0] = 1


@fails
@timeout_settings
@given(integers())
def test_slow_failing_test_2(x):
    time.sleep(0.05)
    assert not calls[1]
    calls[1] = 1


@fails
@given(integers())
@timeout_settings
def test_slow_failing_test_3(x):
    time.sleep(0.05)
    assert not calls[2]
    calls[2] = 1


@fails
@timeout_settings
@given(integers())
def test_slow_failing_test_4(x):
    time.sleep(0.05)
    assert not calls[3]
    calls[3] = 1


@fails
@given(one_of(floats(), booleans()), one_of(floats(), booleans()))
def test_one_of_produces_different_values(x, y):
    assert type(x) == type(y)


@given(just(42))
def test_is_the_answer(x):
    assert x == 42


@fails
@given(text(), text())
def test_text_addition_is_not_commutative(x, y):
    assert x + y == y + x


@fails
@given(binary(), binary())
def test_binary_addition_is_not_commutative(x, y):
    assert x + y == y + x


@given(integers(1, 10))
def test_integers_are_in_range(x):
    assert 1 <= x <= 10


@given(integers(min_value=100))
def test_integers_from_are_from(x):
    assert x >= 100


def test_does_not_catch_interrupt_during_falsify():
    calls = [0]

    @given(integers())
    def flaky_base_exception(x):
        if not calls[0]:
            calls[0] = 1
            raise KeyboardInterrupt()
    with raises(KeyboardInterrupt):
        flaky_base_exception()


def test_contains_the_test_function_name_in_the_exception_string():

    calls = [0]

    @given(integers())
    @settings(max_iterations=10, max_examples=10)
    def this_has_a_totally_unique_name(x):
        calls[0] += 1
        reject()

    with raises(Unsatisfiable) as e:
        this_has_a_totally_unique_name()
        print('Called %d times' % tuple(calls))

    assert this_has_a_totally_unique_name.__name__ in e.value.args[0]

    calls2 = [0]

    class Foo(object):

        @given(integers())
        @settings(max_iterations=10, max_examples=10)
        def this_has_a_unique_name_and_lives_on_a_class(self, x):
            calls2[0] += 1
            reject()

    with raises(Unsatisfiable) as e:
        Foo().this_has_a_unique_name_and_lives_on_a_class()
        print('Called %d times' % tuple(calls2))

    assert (
        Foo.this_has_a_unique_name_and_lives_on_a_class.__name__
    ) in e.value.args[0]


@given(lists(integers()), integers())
def test_removing_an_element_from_a_unique_list(xs, y):
    assume(len(set(xs)) == len(xs))

    try:
        xs.remove(y)
    except ValueError:
        pass

    assert y not in xs


@fails
@given(lists(integers(), average_size=25.0), integers())
def test_removing_an_element_from_a_non_unique_list(xs, y):
    assume(y in xs)
    xs.remove(y)
    assert y not in xs


@given(sets(sampled_from(list(range(10)))))
def test_can_test_sets_sampled_from(xs):
    assert all(isinstance(x, int) for x in xs)
    assert all(0 <= x < 10 for x in xs)


mix = one_of(sampled_from([1, 2, 3]), text())


@fails
@given(mix, mix)
def test_can_mix_sampling_with_generating(x, y):
    assert type(x) == type(y)


@fails
@given(frozensets(integers()))
def test_can_find_large_sum_frozenset(xs):
    assert sum(xs) < 100


def test_prints_on_failure_by_default():
    @given(integers(), integers())
    @settings(max_examples=200, timeout=-1)
    def test_ints_are_sorted(balthazar, evans):
        assume(evans >= 0)
        assert balthazar <= evans
    with raises(AssertionError):
        with capture_out() as out:
            with reporting.with_reporter(reporting.default):
                test_ints_are_sorted()
    out = out.getvalue()
    lines = [l.strip() for l in out.split('\n')]
    assert (
        'Falsifying example: test_ints_are_sorted(balthazar=1, evans=0)'
        in lines)


def test_does_not_print_on_success():
    with settings(verbosity=Verbosity.normal):
        @given(integers())
        def test_is_an_int(x):
            return

        with capture_out() as out:
            test_is_an_int()
    out = out.getvalue()
    lines = [l.strip() for l in out.split(u'\n')]
    assert all(not l for l in lines), lines


@given(sampled_from([1]))
def test_can_sample_from_single_element(x):
    assert x == 1


@fails
@given(lists(integers()))
def test_list_is_sorted(xs):
    assert sorted(xs) == xs


@fails
@given(floats(1.0, 2.0))
def test_is_an_endpoint(x):
    assert x == 1.0 or x == 2.0


def test_breaks_bounds():
    @fails
    @given(x=integers())
    def test_is_bounded(t, x):
        assert x < t
    for t in [1, 10, 100, 1000]:
        test_is_bounded(t)


@given(x=booleans())
def test_can_test_kwargs_only_methods(**kwargs):
    assert isinstance(kwargs['x'], bool)


@fails_with(UnicodeEncodeError)
@given(text())
@settings(max_examples=200)
def test_is_ascii(x):
    x.encode('ascii')


@fails
@given(text())
def test_is_not_ascii(x):
    try:
        x.encode('ascii')
        assert False
    except UnicodeEncodeError:
        pass


@fails
@given(text())
def test_can_find_string_with_duplicates(s):
    assert len(set(s)) == len(s)


@fails
@given(text())
def test_has_ascii(x):
    if not x:
        return
    ascii_characters = (
        u'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ \t\n'
    )
    assert any(c in ascii_characters for c in x)


def test_uses_provided_seed():
    import random
    initial = random.getstate()

    @given(integers())
    @seed(42)
    def test_foo(x):
        pass
    test_foo()
    assert random.getstate() == initial


def test_can_derandomize():
    values = []

    @fails
    @given(integers())
    @settings(derandomize=True, database=None)
    def test_blah(x):
        values.append(x)
        assert x > 0

    test_blah()
    assert values
    v1 = values
    values = []
    test_blah()
    assert v1 == values


def test_can_run_without_database():
    @given(integers())
    @settings(database=None)
    def test_blah(x):
        assert False
    with raises(AssertionError):
        test_blah()


def test_can_run_with_database_in_thread():
    results = []

    @given(integers())
    def test_blah(x):
        assert False

    def run_test():
        try:
            test_blah()
        except AssertionError:
            results.append('success')

    # Run once in the main thread and once in another thread. Execution is
    # strictly serial, so no need for locking.
    run_test()
    thread = threading.Thread(target=run_test)
    thread.start()
    thread.join()
    assert results == ['success', 'success']


@given(integers())
def test_can_call_an_argument_f(f):
    # See issue https://github.com/HypothesisWorks/hypothesis-python/issues/38
    # for details
    pass


Litter = namedtuple('Litter', ('kitten1', 'kitten2'))


@given(builds(Litter, integers(), integers()))
def test_named_tuples_are_of_right_type(litter):
    assert isinstance(litter, Litter)


@fails_with(AttributeError)
@given(integers().map(lambda x: x.nope))
@settings(perform_health_check=False)
def test_fails_in_reify(x):
    pass


@given(text(u'a'))
def test_a_text(x):
    assert set(x).issubset(set(u'a'))


@given(text(u''))
def test_empty_text(x):
    assert not x


@given(text(u'abcdefg'))
def test_mixed_text(x):
    assert set(x).issubset(set(u'abcdefg'))


def test_when_set_to_no_simplifies_runs_failing_example_twice():
    failing = [0]

    @given(integers())
    @settings(max_shrinks=0, max_examples=200)
    def foo(x):
        if x > 11:
            note('Lo')
            failing[0] += 1
            assert False

    with settings(verbosity=Verbosity.normal):
        with raises(AssertionError):
            with capture_out() as out:
                foo()
    assert failing == [2]
    assert 'Falsifying example' in out.getvalue()
    assert 'Lo' in out.getvalue()


@given(integers())
@settings(max_examples=1)
def test_should_not_fail_if_max_examples_less_than_min_satisfying(x):
    pass


def nameless_const(x):
    def f(u, v):
        return u
    return functools.partial(f, x)


@given(sets(booleans()).map(nameless_const(2)))
def test_can_map_nameless(x):
    assert x == 2


@given(
    integers(0, 10).flatmap(nameless_const(just(3))))
def test_can_flatmap_nameless(x):
    assert x == 3


def test_can_be_used_with_none_module():
    def test_is_cool(i):
        pass
    test_is_cool.__module__ = None
    test_is_cool = given(integers())(test_is_cool)
    test_is_cool()


def test_does_not_print_notes_if_all_succeed():
    @given(integers())
    @settings(verbosity=Verbosity.normal)
    def test(i):
        note('Hi there')
    with capture_out() as out:
        with reporting.with_reporter(reporting.default):
            test()
        assert not out.getvalue()


def test_prints_notes_once_on_failure():
    @given(lists(integers()))
    @settings(database=None, verbosity=Verbosity.normal)
    def test(xs):
        note('Hi there')
        assert sum(xs) > 100
    with capture_out() as out:
        with reporting.with_reporter(reporting.default):
            with raises(AssertionError):
                test()
        lines = out.getvalue().strip().splitlines()
        assert len(lines) == 2
        assert 'Hi there' in lines


@given(lists(max_size=0))
def test_empty_lists(xs):
    assert xs == []
