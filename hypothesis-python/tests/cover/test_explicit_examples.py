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

import time
from unittest import TestCase

import pytest

from hypothesis import (
    Phase,
    Verbosity,
    assume,
    example,
    given,
    note,
    reporting,
    settings,
)
from hypothesis.errors import DeadlineExceeded, InvalidArgument, MultipleFailures
from hypothesis.strategies import floats, integers, nothing, text
from tests.common.utils import assert_falsifying_output, capture_out


class TestInstanceMethods(TestCase):
    @given(integers())
    @example(1)
    def test_hi_1(self, x):
        assert isinstance(x, int)

    @given(integers())
    @example(x=1)
    def test_hi_2(self, x):
        assert isinstance(x, int)

    @given(x=integers())
    @example(x=1)
    def test_hi_3(self, x):
        assert isinstance(x, int)


def test_kwarg_example_on_testcase():
    class Stuff(TestCase):
        @given(integers())
        @example(x=1)
        def test_hi(self, x):
            assert isinstance(x, int)

    Stuff("test_hi").test_hi()


def test_errors_when_run_with_not_enough_args():
    @given(integers(), int)
    @example(1)
    def foo(x, y):
        pass

    with pytest.raises(TypeError):
        foo()


def test_errors_when_run_with_not_enough_kwargs():
    @given(integers(), int)
    @example(x=1)
    def foo(x, y):
        pass

    with pytest.raises(TypeError):
        foo()


def test_can_use_examples_after_given():
    long_str = "This is a very long string that you've no chance of hitting"

    @example(long_str)
    @given(text())
    def test_not_long_str(x):
        assert x != long_str

    with pytest.raises(AssertionError):
        test_not_long_str()


def test_can_use_examples_before_given():
    long_str = "This is a very long string that you've no chance of hitting"

    @given(text())
    @example(long_str)
    def test_not_long_str(x):
        assert x != long_str

    with pytest.raises(AssertionError):
        test_not_long_str()


def test_can_use_examples_around_given():
    long_str = "This is a very long string that you've no chance of hitting"
    short_str = "Still no chance"

    seen = []

    @example(short_str)
    @given(text())
    @example(long_str)
    def test_not_long_str(x):
        seen.append(x)

    test_not_long_str()
    assert set(seen[:2]) == {long_str, short_str}


@pytest.mark.parametrize(("x", "y"), [(1, False), (2, True)])
@example(z=10)
@given(z=integers())
def test_is_a_thing(x, y, z):
    pass


def test_no_args_and_kwargs():
    with pytest.raises(InvalidArgument):
        example(1, y=2)


def test_no_empty_examples():
    with pytest.raises(InvalidArgument):
        example()


def test_does_not_print_on_explicit_examples_if_no_failure():
    @example(1)
    @given(integers())
    def test_positive(x):
        assert x > 0

    with reporting.with_reporter(reporting.default):
        with pytest.raises(AssertionError):
            with capture_out() as out:
                test_positive()
    out = out.getvalue()
    assert "Falsifying example: test_positive(1)" not in out


def test_prints_output_for_explicit_examples():
    @example(-1)
    @given(integers())
    def test_positive(x):
        assert x > 0

    assert_falsifying_output(test_positive, x=-1)


def test_prints_verbose_output_for_explicit_examples():
    @settings(verbosity=Verbosity.verbose)
    @example("NOT AN INTEGER")
    @given(integers())
    def test_always_passes(x):
        pass

    assert_falsifying_output(
        test_always_passes, x="NOT AN INTEGER", example_type="Trying"
    )


def test_captures_original_repr_of_example():
    @example(x=[])
    @given(integers())
    def test_mutation(x):
        x.append(1)
        assert not x

    assert_falsifying_output(test_mutation, x=[])


def test_examples_are_tried_in_order():
    @example(x=1)
    @example(x=2)
    @given(integers())
    @settings(phases=[Phase.explicit])
    @example(x=3)
    def test(x):
        print("x -> %d" % (x,))

    with capture_out() as out:
        with reporting.with_reporter(reporting.default):
            test()
    ls = out.getvalue().splitlines()
    assert ls == ["x -> 1", "x -> 2", "x -> 3"]


def test_prints_note_in_failing_example():
    @example(x=42)
    @example(x=43)
    @given(integers())
    def test(x):
        note("x -> %d" % (x,))
        assert x == 42

    with capture_out() as out:
        with reporting.with_reporter(reporting.default):
            with pytest.raises(AssertionError):
                test()
    v = out.getvalue()
    print(v)
    assert "x -> 43" in v
    assert "x -> 42" not in v


def test_must_agree_with_number_of_arguments():
    @example(1, 2)
    @given(integers())
    def test(a):
        pass

    with pytest.raises(InvalidArgument):
        test()


def test_runs_deadline_for_examples():
    @example(10)
    @settings(phases=[Phase.explicit])
    @given(nothing())
    def test(x):
        time.sleep(10)

    with pytest.raises(DeadlineExceeded):
        test()


@given(value=floats(0, 1))
@example(value=0.56789)
@pytest.mark.parametrize("threshold", [0.5, 1])
def test_unsatisfied_assumption_during_explicit_example(threshold, value):
    # Regression test, expected to pass / skip depending on parametrize.
    # See https://github.com/HypothesisWorks/hypothesis/issues/2125
    assume(value < threshold)


@pytest.mark.parametrize("exc", [MultipleFailures, AssertionError])
def test_multiple_example_reporting(exc):
    @example(1)
    @example(2)
    @settings(report_multiple_bugs=exc is MultipleFailures, phases=[Phase.explicit])
    @given(integers())
    def inner_test_multiple_failing_examples(x):
        assert x < 2
        assert x < 1

    with pytest.raises(exc):
        inner_test_multiple_failing_examples()
