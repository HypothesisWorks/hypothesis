from hypothesis.produce import Producers
from hypothesis.simplify import DEFAULT_SIMPLIFIERS

class SearchStrategy:
    def __init__(   self, 
                    descriptor,producers = None,
                    simplifiers = None):
        self.descriptor = descriptor
        self.producers = producers or Producers.default()
        self.simplifiers = simplifiers or DEFAULT_SIMPLIFIERS

    def produce(self,size):
        return self.producers.produce(self.descriptor, size)

    def complexity(self,value):
        return 0

    def simplify(self,value):
        return simplifiers.simplify(value)

    def simplify_such_that(self,*args):
        return self.simplifiers.simplify_such_that(*args)
        
