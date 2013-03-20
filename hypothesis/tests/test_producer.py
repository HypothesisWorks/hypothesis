import hypothesis.produce as p
import pytest

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

class Resettable:
    def __init__(self):
        self.current_depth = 0
        self.reset_called = 0   
        self.max_depth = 0

    def reset_state(self):
        self.reset_called += 1

    def spoo(self, n):
        with p.reset_on_exit(self):
            if(n <= 0): return
            self.max_depth += 1
            self.spoo(n - 1)

    def raises_error(self):
        with p.reset_on_exit(self):
            raise ValueError("Oh noes")


def test_resettable_resets_only_once():
    x = Resettable()
    x.spoo(5)
    assert x.reset_called == 1
    assert x.max_depth == 5

def test_resettable_resets_on_erroor():
    x = Resettable()

    with pytest.raises(ValueError):
        x.raises_error()

    assert x.reset_called == 1
