from hypothesis.testannotations import hypothesis
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
@hypothesis(float,float,float)
def test_float_addition_is_associative(x,y,z):
    assert x + (y + z) == (x + y) + z
