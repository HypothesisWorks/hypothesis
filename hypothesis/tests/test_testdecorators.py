from hypothesis.testdecorators import given
from hypothesis.verifier import Verifier
from functools import wraps

import pytest

def fails(ex=AssertionError):
    def invert_test(f):
        @wraps(f)
        def inverted_test(*arguments,**kwargs):
            with pytest.raises(ex):
                f(*arguments,**kwargs)
        return inverted_test
    return invert_test
        
@given(int,int)
def test_int_addition_is_commutative(x,y):
    assert x + y == y + x

@fails()
@given(str,str)
def test_str_addition_is_commutative(x,y):
    assert x + y == y + x
    
@given(int,int,int)
def test_int_addition_is_associative(x,y,z):
    assert x + (y + z) == (x + y) + z

@fails()
@given(float,float,float)
def test_float_addition_is_associative(x,y,z):
    assert x + (y + z) == (x + y) + z

@given([int])
def test_reversing_preserves_integer_addition(xs):
    assert sum(xs) == sum(reversed(xs))

@fails()
@given([float])
def test_reversing_does_not_preserve_integer_addition(xs):
    assert sum(xs) == sum(reversed(xs))

def test_still_minimizes_on_non_assertion_failures():
    @given(int,verifier=Verifier(starting_size=500))
    def is_not_too_large(x):
        if x >= 10: raise ValueError("No, %s is just too large. Sorry" % x)
    
    with pytest.raises(ValueError) as exinfo:
        is_not_too_large()

    assert " 10 " in exinfo.value.message

class TestCases:
    @given(int)
    def test_abs_non_negative(self,x):
        assert abs(x) >= 0

    @fails()
    @given(int)
    def test_int_is_always_negative(self,x):
        assert x < 0

    @fails()
    @given(float,float)
    def test_float_addition_cancels(self,x,y):
        assert x + (y - x) == y
