from hypothesis.simplify import DEFAULT_SIMPLIFIERS

def test_can_remove_pairs():
    def two_more_falses(xs):
        nt = len([x for x in xs if x])
        nf = len(xs) - nt
        return nf == nt + 2

    simplified = DEFAULT_SIMPLIFIERS.simplify_such_that([False, True,False,True,False,True,False], two_more_falses) 

    assert len(simplified) == 2
