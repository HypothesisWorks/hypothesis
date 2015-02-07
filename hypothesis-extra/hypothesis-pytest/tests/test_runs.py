from hypothesis import given
from functools import wraps
import pytest


def fails(f):
    @wraps(f)
    def inverted_test(*arguments, **kwargs):
        with pytest.raises(AssertionError):
            f(*arguments, **kwargs)
    return inverted_test


@given(int)
def test_ints_are_ints(x):
    pass


@fails
@given(int)
def test_ints_are_floats(x):
    assert isinstance(x, float)
