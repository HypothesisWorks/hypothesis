from hypothesis.hashitanyway import HashItAnyway

def hia(x):
    return HashItAnyway(x)

def test_respects_equality_of_ints():
    assert hia(1) == hia(1)
    assert hia(1) != hia(1)

def test_respects_equality_of_lists_of_ints():
    assert hia([1,1]) == hia([1,1])
    assert hia([1,2]) == hia([1,2])

def test_respects_equality_of_types():
    assert hia(int) == hia(int)
    assert hia(int) != hia(str)

def test_respects_equality_of_lists_of_types():
    assert hia([int,str]) == hia([int,str])
    assert hia([str,int]) != hia([int,str])

def test_hashes_lists_deterministically():
    assert hash(hia([int,str])) == hash(hia([int,str]))

def test_works_correctly_as_a_dict_key():
    k1 = hia([int,str]) 
    k2 = hia([int,str]) 

    d = {}
    d[k1]  = "hi"
    assert d[k2] == "hi"
    d[k2] = "bye"
    assert d[k1] == "bye"
    assert len(d) == 1
