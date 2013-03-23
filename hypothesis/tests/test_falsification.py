from hypothesis.verifier import falsify, Unfalsifiable,assume, Verifier
from hypothesis.specmapper import MissingSpecification
from hypothesis.searchstrategy import SearchStrategy,strategy_for, SearchStrategies, one_of
from contextlib import contextmanager
import random
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
    try:
        yield
    finally:
        signal.alarm(0)

def test_can_make_assumptions():
    def is_good(x):
        assume(x > 5)
        return x % 2 == 0
    assert falsify(is_good, int)[0] == 7    

class Foo():
    pass

@strategy_for(Foo)
class FooStrategy(SearchStrategy):
    def produce(self,size):
        return Foo()

def test_can_falsify_types_without_minimizers():
    assert isinstance(falsify(lambda x: False, Foo)[0], Foo)

class Bar():
    def __init__(self,bar=None):
        self.bar = bar

    def size(self):
        s = 0
        while self:
            self = self.bar
            s += 1
        return s

    def __repr__(self):
        return "Bar(%s)" % self.size()
 
    def __eq__(self,other): 
        return isinstance(other, Bar) and self.size() == other.size()

class BarStrategy(SearchStrategy):
    def __init__(self,strategies,descriptor):
        SearchStrategy.__init__(self,strategies,descriptor)
        self.int_strategy = strategies.strategy(int)

    def produce(self, size):
        x = Bar()
        for _ in xrange(self.int_strategy.produce(size)):
            x = Bar(x)
        return x

    def simplify(self, bar):
        while True:
            bar = bar.bar
            if bar: yield bar
            else: return 
     
def test_can_falsify_types_without_default_productions():
    strategies = SearchStrategies()
    strategies.define_specification_for(Bar, BarStrategy)

    with pytest.raises(MissingSpecification):
        SearchStrategies.default().strategy(Bar)

    verifier = Verifier(search_strategies = strategies)
    assert verifier.falsify(lambda x : False, Bar,)[0] == Bar()
    assert verifier.falsify(lambda x : x.size() < 3, Bar)[0] == Bar(Bar(Bar()))
    

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

def test_can_find_negative_floats():
    assert falsify(lambda x : x > -1.0, float)[0] == -1.0

def test_can_falsify_int_pairs():
    assert falsify(lambda x,y: x > y, int,int) == (0,0)

def test_can_falsify_string_commutativity():
    assert tuple(sorted(falsify(lambda x,y: x + y == y + x,str,str))) == ('0','1')

def test_can_falsify_sets():
    assert falsify(lambda x: not x, {int})[0] == {0}

def test_can_falsify_list_inclusion():
    assert falsify(lambda x,y: x not in y, int, [int]) == (0,[0])

def test_can_falsify_set_inclusion():
    assert falsify(lambda x,y: x not in y, int, {int}) == (0,{0})

def test_can_falsify_lists():
    assert falsify(lambda x: len(x) < 3, [int])[0] == [0] * 3

def test_can_falsify_long_lists():
    assert falsify(lambda x: len(x) < 20, [int],warming_rate=0.5)[0] == [0] * 20 

def test_can_find_unsorted_lists():
    unsorted = falsify(lambda x: sorted(x) == x, [int])[0] 
    assert unsorted == [1,0] or unsorted == [0,-1]

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


def test_can_falsify_alternating_types():
    falsify(lambda x: isinstance(x, int), one_of([int, str]))[0] == ""

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


def test_stops_loop_pretty_quickly():
    with pytest.raises(Unfalsifiable):
        with timeout(5):
            falsify(lambda x: x == x, int)

def test_good_errors_on_bad_values():
    some_string = "I am the very model of a modern major general"
    with pytest.raises(MissingSpecification) as e:
        falsify(lambda x: False, some_string)

    assert some_string in e.value.message

def test_can_falsify_bools():
    assert falsify(lambda x: x, bool)[0] == False

