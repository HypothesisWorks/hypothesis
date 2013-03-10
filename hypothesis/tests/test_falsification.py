from hypothesis.testing import falsify, Unfalsifiable
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

def test_can_falsify_string_matching():
    # Note that just doing a match("foo",x) will never find a good solution
    # because the state space is too large
    assert falsify(lambda x: not re.match(".*f.*o.*o.*",x), str)[0] == "foo"

def tst_can_falsify_floats():
    x,y,z = falsify(lambda x,y,z: (x + y) + z == x + (y +z), float,float,float)
    assert (x + y) + z != x + (y + z)

def test_can_falsify_ints():
   assert falsify(lambda x: x != 0, int) == (0,)

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
