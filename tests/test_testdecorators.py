from hypothesis.testdecorators import given
from hypothesis.verifier import Verifier, assume, Unsatisfiable
from hypothesis.descriptors import one_of, just, integers_in_range
from functools import wraps
import pytest
import time
from six import text_type, binary_type
import hypothesis.settings as hs


def fails_with(e):
    def accepts(f):
        @wraps(f)
        def inverted_test(*arguments, **kwargs):
            with pytest.raises(e):
                f(*arguments, **kwargs)
        return inverted_test
    return accepts

fails = fails_with(AssertionError)


@given(int, int)
def test_int_addition_is_commutative(x, y):
    assert x + y == y + x


@fails
@given(str, str)
def test_str_addition_is_commutative(x, y):
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
@given(int, verifier_settings=hs.Settings(timeout=0.1))
def test_slow_test_times_out(x):
    time.sleep(0.05)


# Cheap hack to make test functions which fail on their second invocation
calls = [0, 0, 0, 0]

timeout_settings = hs.Settings(timeout=0.2)


# The following tests exist to test that verifiers start their timeout
# from when the test first executes, not from when it is defined.
@fails
@given(int, verifier_settings=timeout_settings)
def test_slow_failing_test_1(x):
    time.sleep(0.05)
    assert not calls[0]
    calls[0] = 1


@fails
@given(int, verifier_settings=timeout_settings)
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

    @given(int)
    def this_has_a_totally_unique_name(x):
        assume(False)

    with pytest.raises(Unsatisfiable) as e:
        this_has_a_totally_unique_name()

    assert this_has_a_totally_unique_name.__name__ in e.value.args[0]

    class Foo(object):
        @given(int)
        def this_has_a_unique_name_and_lives_on_a_class(self, x):
            assume(False)

    with pytest.raises(Unsatisfiable) as e:
        Foo().this_has_a_unique_name_and_lives_on_a_class()

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
