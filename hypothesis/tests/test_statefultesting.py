from hypothesis.statefultesting import StatefulTest, step, precondition, integrity_test
from hypothesis.verifier import assume


class Foo(StatefulTest):
    @integrity_test
    def are_you_still_there(self): 
        assert True

    @step
    def blargh(self): pass

    def bar(self): pass

    @step
    def baz(self): pass

def test_picks_up_only_annotated_methods_as_operations():
    assert len(Foo.test_steps()) == 2
    assert len(Foo.integrity_tests()) == 1

class BrokenCounter(StatefulTest):
    def __init__(self):
        self.value = 0

    @step
    def inc(self):
        start_value = self.value
        self.value += 1
        assert self.value == start_value + 1

    @step
    def dec(self):
        precondition(self.value > 0)
        start_value = self.value
        if(self.value != 5): self.value -= 1
        assert self.value == start_value - 1

def test_finds_broken_example():
    assert [x.__name__ for x in BrokenCounter.breaking_example()] == ['inc'] * 5 + ['dec']

