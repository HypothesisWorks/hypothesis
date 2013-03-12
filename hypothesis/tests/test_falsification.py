from hypothesis.testing import falsify, Unfalsifiable,assume
from hypothesis.produce import generates;
from contextlib import contextmanager
import pytest
import re
import signal

class TimeoutError(Exception):
    pass

@contextmanager
def timeout(time):
    def timed_out(signum,frame):
        signal.alarm(0)
        raise TimeoutError()
        
    signal.signal(signal.SIGALRM, timed_out)
    signal.alarm(time)
    yield
    signal.alarm(0)

def test_can_make_assumptions():
    def is_good(x):
        assume(x > 5)
        return x % 2 == 0
    assert falsify(is_good, int)[0] == 7    

class Foo():
    pass

@generates(Foo)
def foo(size):
    while True:
        yield Foo()

def test_can_falsify_types_without_minimizers():
    assert isinstance(falsify(lambda x: False, Foo)[0], Foo)

def test_can_falsify_mixed_lists():
    def is_pure(xs):
        for a in xs:
            for b in xs:
                if a.__class__ != b.__class__:
                    return False
        return True

    xs = falsify(is_pure, [int,str])[0]
    assert len(xs) == 2
    assert 0 in xs
    assert "" in xs

def test_can_falsify_tuples():
    def out_of_order_positive_tuple(x):
        a,b = x
        assume(a > 0 and b > 0)
        assert a >= b
        return True
    assert falsify(out_of_order_positive_tuple, (int,int))[0] == (1,2)

def test_can_falsify_dicts():
    def is_good(x):
        assume("foo" in x)
        assume("bar" in x) 
        return x["foo"] < x["bar"]
    assert falsify(is_good, {"foo": int, "bar" : int})[0] == {"foo" : 0, "bar" : 0}
   

def test_can_falsify_string_matching():
    # Note that just doing a match("foo",x) will never find a good solution
    # because the state space is too large
    assert falsify(lambda x: not re.search("a.*b",x), str)[0] == "ab"

def test_minimizes_strings_to_zeroes():
    assert falsify(lambda x: len(x) < 3, str)[0] == "000"

def test_can_find_short_strings():
    assert falsify(lambda x: len(x) > 0, str)[0] == ""
    assert len(falsify(lambda x: len(x) <= 1, str)[0]) == 2
    assert falsify(lambda x : len(x) < 10, [str])[0] == [""] * 10

def test_can_falsify_assertions():
    def is_good(x):
        assert x < 3
        return True
    assert falsify(is_good, int)[0] == 3

def test_can_falsify_floats():
    x,y,z = falsify(lambda x,y,z: (x + y) + z == x + (y +z), float,float,float)
    assert (x + y) + z != x + (y + z)

def test_can_falsify_ints():
    assert falsify(lambda x: x != 0, int)[0] == 0

def test_can_find_negative_ints():
    assert falsify(lambda x: x >= 0, int)[0] == -1 

def test_can_falsify_int_pairs():
    assert falsify(lambda x,y: x > y, int,int) == (0,0)

def test_can_falsify_lists():
    assert falsify(lambda x: len(x) < 3, [int])[0] == [0] * 3
    assert falsify(lambda x: len(x) < 50, [int])[0] == [0] * 50 

def test_can_find_unsorted_lists():
    unsorted = falsify(lambda x: sorted(x) == x, [int])[0] 
    assert unsorted == [1,0] or unsorted == [0,-1]

def test_stops_loop_pretty_quickly():
    with pytest.raises(Unfalsifiable):
        with timeout(5):
            falsify(lambda x: x == x, int)
