from hypothesis.testdecorators import hypothesis
from functools import wraps

import pytest

def fails(f):
    @wraps(f)
    def inverted_test(*arguments,**kwargs):
        with pytest.raises(AssertionError):
            f(*arguments,**kwargs)
    return inverted_test
        
@hypothesis(int,int)
def test_int_addition_is_commutative(x,y):
    assert x + y == y + x

@fails
@hypothesis(str,str)
def test_str_addition_is_commutative(x,y):
    assert x + y == y + x
    
@hypothesis(int,int,int)
def test_int_addition_is_associative(x,y,z):
    assert x + (y + z) == (x + y) + z

@fails
@hypothesis(float,float,float)
def test_float_addition_is_associative(x,y,z):
    assert x + (y + z) == (x + y) + z

@hypothesis([int])
def test_reversing_preserves_integer_addition(xs):
    assert sum(xs) == sum(reversed(xs))

@fails
@hypothesis([float])
def test_reversing_does_not_preserve_integer_addition(xs):
    assert sum(xs) == sum(reversed(xs))


