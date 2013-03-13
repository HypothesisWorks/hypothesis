from hypothesis.testdecorators import given
from functools import wraps

import pytest

def fails(f):
    @wraps(f)
    def inverted_test(*arguments,**kwargs):
        with pytest.raises(AssertionError):
            f(*arguments,**kwargs)
    return inverted_test
        
@given(int,int)
def test_int_addition_is_commutative(x,y):
    assert x + y == y + x

@fails
@given(str,str)
def test_str_addition_is_commutative(x,y):
    assert x + y == y + x
    
@given(int,int,int)
def test_int_addition_is_associative(x,y,z):
    assert x + (y + z) == (x + y) + z

@fails
@given(float,float,float)
def test_float_addition_is_associative(x,y,z):
    assert x + (y + z) == (x + y) + z

@given([int])
def test_reversing_preserves_integer_addition(xs):
    assert sum(xs) == sum(reversed(xs))

@fails
@given([float])
def test_reversing_does_not_preserve_integer_addition(xs):
    assert sum(xs) == sum(reversed(xs))

class TestCases:
    @given(int)
    def test_abs_non_negative(self,x):
        assert abs(x) >= 0

    @fails
    @given(int)
    def test_int_is_always_negative(self,x):
        assert x < 0

    @fails
    @given(float,float)
    def test_float_addition_cancels(self,x,y):
        assert x + (y - x) == y
