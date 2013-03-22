from hypothesis.produce import Producers
from hypothesis.simplify import DEFAULT_SIMPLIFIERS
from hypothesis.specmapper import SpecificationMapper
from hypothesis.tracker import Tracker

from abc import abstractmethod
from math import log, log1p
from random import random

def strategy_for(typ):
    def accept_function(fn):
        SearchStrategies.default().define_specification_for(typ, fn)
        return fn
    return accept_function

def strategy_for_instances(typ):
    def accept_function(fn):
        SearchStrategies.default().define_specification_for_instances(typ, fn)
        return fn
    return accept_function

class SearchStrategies(SpecificationMapper):
    def strategy(self, *args, **kwargs):
        return self.specification_for(*args, **kwargs)

class SearchStrategy:
    def __init__(   self,
                    strategies,
                    descriptor):
        self.descriptor = descriptor

    @abstractmethod
    def produce(self,size):
        pass

    def complexity(self,value):
        return 0

    def simplify(self,value):
        return iter(())

    def simplify_such_that(self, t, f):
        tracker = Tracker()

        while True:
            for s in self.simplify(t):
                if tracker.track(s) > 1: 
                    continue

                if f(s):
                    t = s
                    break
            else:
                return t  

@strategy_for(int)
class IntStrategy(SearchStrategy):
    def complexity(self, value):
        if value >= 0: return value
        else: return 1 - value

    def geometric_probability_for_entropy(desired_entropy):
        def h(p):
            if p <= 0:
                return float('inf')
            if p >= 1:
                return 0
            try:
                q = 1 - p
                return -(q * log(q) + p * log(p))/(log(2) * p)
            except ValueError:
                return 0.0
        lower = 0.0
        upper = 1.0
        for _ in xrange(max(int(desired_entropy * 2), 1024)):
            mid = (lower + upper) / 2
            if h(mid) > desired_entropy:
                lower = mid
            else:
                upper = mid
        return mid

    def produce(self,size):
        can_be_negative = size > 1
      
        if size <= 0:
            return 0
     
        if can_be_negative:
            size -= 1
        p = 1.0 / (size + 1)
        n =  int(log(random()) / log1p(- p))
        if can_be_negative and random() <= 0.5:
            n = -n
        return n

    def simplify(self, x):
        if x < 0:
            yield -x
            for y in self.simplify(-x): yield -y
        elif x == 2:
            yield 1
            yield 0
        elif x == 1:
            yield 0
        elif x == 0:
            pass
        else:
            yield x - 1
            yield x / 2
            for y in self.simplify(x - 1): yield y
            for y in self.simplify(x / 2): yield y

@strategy_for_instances(tuple)
class TupleStrategy(SearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor):
        SearchStrategy.__init__(self, strategies, descriptor)
        self.element_strategies = tuple((strategies.strategy(x) for x in descriptor))

    def complexity(self, xs):
        return sum((s.complexity(x) for s,x in zip(self.element_strategies, xs)))

    def produce(self, size):
        es = self.element_strategies
        return tuple([g.produce(size/len(es)) for g in es])

    def simplify(self, x):
        """
        Defined simplification for tuples: We don't change the length of the tuple
        we only try to simplify individual elements of it.
        We first try simplifying each index. We then try pairs of indices.
        After that we stop because it's getting silly. 
        """

        for i in xrange(0, len(x)):
            for s in self.element_strategies[i].simplify(x[i]):
                z = list(x)
                z[i] = s
                yield tuple(z)
        for i in xrange(0, len(x)):
            for j in xrange(0, len(x)):
                if i == j: continue
                for s in self.element_strategies[i].simplify(x[i]):
                    for t in self.element_strategies[j].simplify(x[j]):
                        z = list(x)
                        z[i] = s
                        z[j] = t
                        yield tuple(z)
