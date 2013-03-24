import hypothesis.searchstrategy as ss
from hypothesis.flags import Flags
from hypothesis.tracker import Tracker

def strategy(*args,**kwargs):
    return ss.SearchStrategies().strategy(*args,**kwargs)

def test_tuples_inspect_component_types_for_production():
    strxint = strategy((str,int))

    assert strxint.could_have_produced(("", 2))
    assert not strxint.could_have_produced((2, 2))

    intxint = strategy((int,int))
    
    assert not intxint.could_have_produced(("", 2))
    assert intxint.could_have_produced((2, 2))

def alternating(*args):
    return strategy(ss.one_of(args))

def minimize(s, x):
    return s.simplify_such_that(x, lambda _: True)

def test_can_minimize_component_types():
    ios = alternating(str, int)
    assert 0  == minimize(ios, 10)
    assert "" == minimize(ios, "I like kittens")

def test_can_minimize_nested_component_types():
    ios = alternating((int,str), (int,int))
    assert (0,"") == minimize(ios, (42, "I like kittens"))
    assert (0,0)  == minimize(ios, (42, 666))

def test_can_minimize_tuples():
    ts = strategy((int,int,int))
    assert minimize(ts, (10,10,10)) == (0,0,0)

def assert_no_duplicates_in_simplify(s, x):
    s = strategy(s)
    t = Tracker()
    t.track(x)
    for y in s.simplify(x):
        assert t.track(y) == 1

def test_ints_no_duplicates_in_simplify():
    assert_no_duplicates_in_simplify(int, 555)

def test_int_lists_no_duplicates_in_simplify():
    assert_no_duplicates_in_simplify([int], [0, 555, 1281])

def test_float_lists_no_duplicates_in_simplify():
    assert_no_duplicates_in_simplify([float], [0.5154278802175156, 555.0, 1281.8556018727038])

def test_just_works():
    s = strategy(ss.just("giving"))
    assert s.produce(10,Flags()) == "giving"
    assert s.simplify_such_that("giving", lambda _ : True) == "giving"

