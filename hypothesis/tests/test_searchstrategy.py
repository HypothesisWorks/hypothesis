import hypothesis.searchstrategy as ss

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
    while True:
        try:
            x = next(s.simplify(x))
        except StopIteration:
            break
    return x

def test_can_minimize_component_types():
    ios = alternating(str, int)
    assert 0  == minimize(ios, 10)
    assert "" == minimize(ios, "I like kittens")

def test_can_minimize_nested_component_types():
    ios = alternating((int,str), (int,int))
    assert (0,"") == minimize(ios, (42, "I like kittens"))
    assert (0,0)  == minimize(ios, (42, 666))
