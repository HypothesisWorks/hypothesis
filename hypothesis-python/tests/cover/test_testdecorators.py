# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import functools
import threading
from collections import namedtuple

from hypothesis import (
    HealthCheck,
    Verbosity,
    assume,
    given,
    note,
    reporting,
    settings,
    strategies as st,
)
from hypothesis.errors import Unsatisfiable
from hypothesis.strategies import (
    binary,
    booleans,
    builds,
    data,
    floats,
    frozensets,
    integers,
    just,
    lists,
    one_of,
    sampled_from,
    sets,
    text,
)

from tests.common.utils import (
    Why,
    assert_falsifying_output,
    capture_out,
    fails,
    fails_with,
    no_shrink,
    raises,
    skipif_emscripten,
    xfail_on_crosshair,
)
from tests.conjecture.common import buffer_size_limit

# This particular test file is run under both pytest and nose, so it can't
# rely on pytest-specific helpers like `pytest.raises` unless we define a
# fallback in tests.common.utils.


@given(integers(), integers())
def test_int_addition_is_commutative(x, y):
    assert x + y == y + x


@fails
@given(text(min_size=1), text(min_size=1))
def test_str_addition_is_commutative(x, y):
    assert x + y == y + x


@fails
@given(binary(min_size=1), binary(min_size=1))
def test_bytes_addition_is_commutative(x, y):
    # We enforce min_size=1 here to avoid a rare flakiness, where the
    # test passes if x and/or y are b"" for every generated example.
    # (the internal implementation makes this less rare for bytes)
    assert x + y == y + x


@given(integers(), integers(), integers())
def test_int_addition_is_associative(x, y, z):
    assert x + (y + z) == (x + y) + z


@fails
@given(floats(), floats(), floats())
@settings(max_examples=2000)
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
            raise ValueError(f"No, {x} is just too large. Sorry")

    with raises(ValueError, match=" 10 "):
        is_not_too_large()


@given(integers())
def test_integer_division_shrinks_positive_integers(n):
    assume(n > 0)
    assert n / 2 < n


class TestCases:
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
        assert abs(kw["x"]) >= 0
        assert isinstance(self, TestCases)

    @given(x=integers())
    def test_abs_non_negative_varargs_kwargs_only(*args, **kw):
        assert abs(kw["x"]) >= 0
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


@fails
@given(one_of(floats(), booleans()), one_of(floats(), booleans()))
def test_one_of_produces_different_values(x, y):
    assert type(x) == type(y)


@given(just(42))
def test_is_the_answer(x):
    assert x == 42


@given(integers(1, 10))
def test_integers_are_in_range(x):
    assert 1 <= x <= 10


@given(integers(min_value=100))
def test_integers_from_are_from(x):
    assert x >= 100


def test_does_not_catch_interrupt_during_falsify():
    called = False

    @given(integers())
    def flaky_base_exception(x):
        nonlocal called
        if not called:
            called = True
            raise KeyboardInterrupt

    with raises(KeyboardInterrupt):
        flaky_base_exception()


@given(lists(integers(), unique=True), integers())
def test_removing_an_element_from_a_unique_list(xs, y):
    assume(len(set(xs)) == len(xs))

    try:
        xs.remove(y)
    except ValueError:
        pass

    assert y not in xs


@fails
@given(lists(integers(), min_size=2), data())
def test_removing_an_element_from_a_non_unique_list(xs, data):
    y = data.draw(sampled_from(xs))
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
    @settings(max_examples=100)
    def test_ints_are_sorted(balthazar, evans):
        assume(evans >= 0)
        assert balthazar <= evans

    assert_falsifying_output(test_ints_are_sorted, balthazar=1, evans=0)


def test_does_not_print_on_success():
    @settings(verbosity=Verbosity.normal)
    @given(integers())
    def test_is_an_int(x):
        return

    with capture_out() as out:
        test_is_an_int()
    out = out.getvalue()
    lines = [l.strip() for l in out.split("\n")]
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
    @settings(derandomize=True, max_examples=10_000)
    def test_is_bounded(t, x):
        assert x < t

    for t in [1, 10, 100, 1000]:
        test_is_bounded(t)


@given(x=booleans())
def test_can_test_kwargs_only_methods(**kwargs):
    assert isinstance(kwargs["x"], bool)


@fails_with(UnicodeEncodeError)
@given(text())
@settings(max_examples=100)
def test_is_ascii(x):
    x.encode("ascii")


@fails
@given(text())
def test_is_not_ascii(x):
    try:
        x.encode("ascii")
        raise AssertionError
    except UnicodeEncodeError:
        pass


@fails
@given(text(min_size=2))
@settings(max_examples=100, derandomize=True)
def test_can_find_string_with_duplicates(s):
    assert len(set(s)) == len(s)


@fails
@given(text(min_size=1))
@settings(derandomize=True)
def test_has_ascii(x):
    if not x:
        return
    ascii_characters = (
        "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ \t\n"
    )
    assert any(c in ascii_characters for c in x)


@xfail_on_crosshair(Why.symbolic_outside_context, strict=False)
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
        raise AssertionError

    with raises(AssertionError):
        test_blah()


@skipif_emscripten
def test_can_run_with_database_in_thread():
    results = []

    @given(integers())
    def test_blah(x):
        raise ValueError

    def run_test():
        try:
            test_blah()
        except ValueError:
            results.append("success")

    # Run once in the main thread and once in another thread. Execution is
    # strictly serial, so no need for locking.
    run_test()
    assert results == ["success"]
    thread = threading.Thread(target=run_test)
    thread.start()
    thread.join()
    assert results == ["success", "success"]


@given(integers())
def test_can_call_an_argument_f(f):
    # See issue https://github.com/HypothesisWorks/hypothesis-python/issues/38
    # for details
    pass


Litter = namedtuple("Litter", ("kitten1", "kitten2"))


@given(builds(Litter, integers(), integers()))
def test_named_tuples_are_of_right_type(litter):
    assert isinstance(litter, Litter)


@fails_with(AttributeError)
@given(integers().map(lambda x: x.nope))
@settings(suppress_health_check=list(HealthCheck))
def test_fails_in_reify(x):
    pass


@given(text("a"))
def test_a_text(x):
    assert set(x).issubset(set("a"))


@given(text(""))
def test_empty_text(x):
    assert not x


@given(text("abcdefg"))
def test_mixed_text(x):
    assert set(x).issubset(set("abcdefg"))


@xfail_on_crosshair(Why.other, strict=False)  # runs ~five failing examples
def test_when_set_to_no_simplifies_runs_failing_example_twice():
    failing = []

    @given(integers())
    @settings(
        phases=no_shrink,
        max_examples=100,
        verbosity=Verbosity.normal,
        report_multiple_bugs=False,
    )
    def foo(x):
        if x > 11:
            note("Lo")
            failing.append(x)
            raise AssertionError

    with raises(AssertionError) as err:
        foo()
    assert len(failing) == 2
    assert len(set(failing)) == 1
    assert "Falsifying example" in "\n".join(err.value.__notes__)
    assert "Lo" in err.value.__notes__


@given(integers().filter(lambda x: x % 4 == 0))
def test_filtered_values_satisfy_condition(i):
    assert i % 4 == 0


def nameless_const(x):
    def f(u, v):
        return u

    return functools.partial(f, x)


@given(sets(booleans()).map(nameless_const(2)))
def test_can_map_nameless(x):
    assert x == 2


@given(integers(0, 10).flatmap(nameless_const(just(3))))
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
        note("Hi there")

    with capture_out() as out:
        with reporting.with_reporter(reporting.default):
            test()
    assert not out.getvalue()


def test_prints_notes_once_on_failure():
    @given(lists(integers()))
    @settings(database=None, verbosity=Verbosity.normal)
    def test(xs):
        note("Hi there")
        if sum(xs) <= 100:
            raise ValueError

    with raises(ValueError) as err:
        test()
    assert err.value.__notes__.count("Hi there") == 1


@given(lists(integers(), max_size=0))
def test_empty_lists(xs):
    assert xs == []


@xfail_on_crosshair(Why.other, strict=False)
def test_given_usable_inline_on_lambdas():
    xs = []
    given(booleans())(lambda x: xs.append(x))()
    assert len(xs) == 2
    assert set(xs) == {False, True}


def test_notes_high_filter_rates_in_unsatisfiable_error():
    @given(st.integers())
    @settings(suppress_health_check=[HealthCheck.filter_too_much])
    def f(v):
        assume(False)

    with raises(
        Unsatisfiable,
        match=(
            r"Unable to satisfy assumptions of f\. 1000 of 1000 examples "
            r"failed a \.filter\(\) or assume\(\)"
        ),
    ):
        f()


# crosshair generates one valid input before verifying the test function,
# so the Unsatisfiable check never occurs.
# (not strict due to slowness causing crosshair to bail out on the first input,
# maybe?)
@xfail_on_crosshair(Why.other, strict=False)
def test_notes_high_overrun_rates_in_unsatisfiable_error():
    @given(st.binary(min_size=100))
    @settings(
        suppress_health_check=[
            HealthCheck.data_too_large,
            HealthCheck.too_slow,
            HealthCheck.large_base_example,
        ]
    )
    def f(v):
        pass

    with (
        raises(
            Unsatisfiable,
            match=(
                r"1000 of 1000 examples were too large to finish generating; "
                r"try reducing the typical size of your inputs\?"
            ),
        ),
        buffer_size_limit(10),
    ):
        f()
