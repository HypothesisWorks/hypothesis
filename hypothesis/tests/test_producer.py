import hypothesis.produce as p

def f(*args): pass

class Foo():
    def g(*args): pass
    
    @classmethod
    def h(*args): pass

def test_leaves_producer_methods_untouched():
    prods = p.Producers()

    assert prods.producer(f) == f
    assert prods.producer(Foo.h) == Foo.h
    assert prods.producer(Foo.g) == Foo.g
    x = Foo()
    assert prods.producer(x.g) == x.g

def test_produces_an_empty_tuple():
    prods = p.Producers()
    assert prods.produce((), 1) == ()

