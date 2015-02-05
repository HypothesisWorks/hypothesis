import inspect
import pytest
from hypothesis import given


def has_one_arg(hello):
    pass


def has_two_args(hello, world):
    pass


def has_a_default(x, y, z=1):
    pass


def has_varargs(*args):
    pass


def has_kwargs(**kwargs):
    pass

basic_test_cases = [
    (has_one_arg, given()),
    (has_one_arg, given(int)),
    (has_one_arg, given(hello=int)),
    (has_two_args, given()),
    (has_two_args, given(int)),
    (has_two_args, given(int, bool)),
    (has_a_default, given(int, int)),
    (has_a_default, given(int, int, int)),
    (has_varargs, given()),
    (has_varargs, given(int, bool, bool)),
    (has_kwargs, given(a=int, b=int, c=bool)),
]


@pytest.mark.parametrize('f,g', basic_test_cases)
def test_argspec_lines_up(f, g):
    af = inspect.getargspec(f)
    ag = inspect.getargspec(g(f))
    assert af.args == ag.args
    assert af.keywords == ag.keywords
    assert af.varargs == ag.varargs
