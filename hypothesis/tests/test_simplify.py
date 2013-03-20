from hypothesis.simplify import DEFAULT_SIMPLIFIERS

def test_can_remove_pairs_from_lists():
    def two_more_falses(xs):
        nt = len([x for x in xs if x])
        nf = len(xs) - nt
        return nf == nt + 2

    simplified = DEFAULT_SIMPLIFIERS.simplify_such_that([False, True,False,True,False,True,False], two_more_falses) 

    assert len(simplified) == 2

def test_can_simplify_pairs_in_lists():
    # Expected route to simplification: Decrement size of both sides by 1 until 
    # you have [0,0]. It's now safe to remove items.
    assert DEFAULT_SIMPLIFIERS.simplify_such_that([5,-5], lambda p: sum(p) == 0) == []

def test_can_simplify_pairs_of_ints():
    assert DEFAULT_SIMPLIFIERS.simplify_such_that((5,-5), lambda p: sum(p) == 0) == (0,0)

