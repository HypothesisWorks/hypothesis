# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

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
from hypothesis.errors import DeadlineExceeded, HypothesisWarning, InvalidArgument
from hypothesis.internal.compat import ExceptionGroup
from hypothesis.strategies import floats, integers, text

from tests.common.utils import assert_falsifying_output, capture_out, fails_with


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

    assert_falsifying_output(test_positive, "Falsifying explicit", x=-1)


def test_prints_verbose_output_for_explicit_examples():
    @settings(verbosity=Verbosity.verbose)
    @example("NOT AN INTEGER")
    @given(integers())
    def test_always_passes(x):
        pass

    assert_falsifying_output(
        test_always_passes,
        expected_exception=None,
        example_type="Trying explicit",
        x="NOT AN INTEGER",
    )


def test_captures_original_repr_of_example():
    @example(x=[])
    @given(integers())
    def test_mutation(x):
        x.append(1)
        assert not x

    assert_falsifying_output(test_mutation, "Falsifying explicit", x=[])


def test_examples_are_tried_in_order():
    @example(x=1)
    @example(x=2)
    @given(integers())
    @settings(phases=[Phase.explicit])
    @example(x=3)
    def test(x):
        print(f"x -> {x}")

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
        note(f"x -> {x}")
        assert x == 42

    with pytest.raises(AssertionError) as err:
        test()
    assert "x -> 43" in err.value.__notes__
    assert "x -> 42" not in err.value.__notes__


def test_must_agree_with_number_of_arguments():
    @example(1, 2)
    @given(integers())
    def test(a):
        pass

    with pytest.raises(InvalidArgument):
        test()


@fails_with(DeadlineExceeded)
@example(10)
@settings(phases=[Phase.explicit], deadline=1)
@given(integers())
def test(x):
    time.sleep(10)


@given(value=floats(0, 1))
@example(value=0.56789)
@pytest.mark.parametrize("threshold", [0.5, 1])
def test_unsatisfied_assumption_during_explicit_example(threshold, value):
    # Regression test, expected to pass / skip depending on parametrize.
    # See https://github.com/HypothesisWorks/hypothesis/issues/2125
    assume(value < threshold)


@pytest.mark.parametrize("exc", [ExceptionGroup, AssertionError])
def test_multiple_example_reporting(exc):
    @example(1)
    @example(2)
    @settings(report_multiple_bugs=exc is ExceptionGroup, phases=[Phase.explicit])
    @given(integers())
    def inner_test_multiple_failing_examples(x):
        assert x < 2
        assert x < 1

    with pytest.raises(exc):
        inner_test_multiple_failing_examples()


@example(text())
@given(text())
def test_example_decorator_accepts_strategies(s):
    """The custom error message only happens when the test has already failed."""


def test_helpful_message_when_example_fails_because_it_was_passed_a_strategy():
    @example(text())
    @given(text())
    def t(s):
        assert isinstance(s, str)

    try:
        t()
    except HypothesisWarning as err:
        assert isinstance(err.__cause__, AssertionError)
    else:
        raise NotImplementedError("should be unreachable")


def test_stop_silently_dropping_examples_when_decorator_is_applied_to_itself():
    def f():
        pass

    test = example("outer")(example("inner"))(f)
    assert len(test.hypothesis_explicit_examples) == 2
