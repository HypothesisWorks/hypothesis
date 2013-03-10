from hypothesis.testing import falsify, Unfalsifiable
from contextlib import contextmanager
import pytest

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

def test_can_falsify_ints():
   assert falsify(lambda x: x != 0, int) == (0,)

def test_can_falsify_int_pairs():
    assert falsify(lambda x,y: x > y, int,int) == (0,0)

def test_stops_loop_pretty_quickly():
    with pytest.raises(Unfalsifiable):
        with timeout(5):
            falsify(lambda x: x == x, int)
