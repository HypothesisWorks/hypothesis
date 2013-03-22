from hypothesis.produce import Producers
from hypothesis.simplify import DEFAULT_SIMPLIFIERS
from hypothesis.specmapper import SpecificationMapper
from hypothesis.tracker import Tracker

from abc import abstractmethod
from math import log, log1p
from random import random,choice

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

@strategy_for_instances(list)
class ListStrategy(SearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor,
                    **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor,**kwargs)
        if len(descriptor) != 1:
            raise ValueError("Cannot produce instances from lists of length != 1: (%s)" % str(descriptor))

        self.element_strategy = strategies.strategy(descriptor[0])
        self.length_strategy = strategies.strategy(int)
        self.length_entropy = kwargs.get("length_entropy", 0.25)

    def produce(self, size):
        length = self.length_strategy.produce(size * self.length_entropy)
        if length == 0:
            return []
        element_entropy = (1.0 - self.length_entropy) / length
        return [self.element_strategy.produce(element_entropy) for _ in xrange(length)]

class OneCharStringStrategy(SearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor,
                    **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor,**kwargs)
        self.characters = kwargs.get('characters', map(chr,range(0,127)))
        self.zero_point = kwargs.get('zero_point', ord('0'))

    def produce(self, size):
        return choice(self.characters)

    def complexity(self, x):
        return abs(ord(x) - self.zero_point)
        

class MappedSearchStrategy(SearchStrategy):
    @abstractmethod
    def pack(self, x):
        pass

    @abstractmethod
    def unpack(self, x):
        pass

    def produce(self, size):
        return self.pack(self.mapped_strategy.produce(size))

    def complexity(self, x):
        return self.mapped_strategy.complexity(self.unpack(x))

    def simplify(self, x):
        for y in self.mapped_strategy.simplify(self.unpack(x)):
            yield self.pack(x)


@strategy_for(str)
class StringStrategy(MappedSearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor,
                    **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor,**kwargs)
        self.length_strategy = strategies.strategy(int)
        self.char_strategy = kwargs.get("char_strategy", OneCharStringStrategy)
        
        cs = strategies.new_child_mapper()
        cs.define_specification_for(str, self.char_strategy)
        self.mapped_strategy = cs.strategy([str])

    def pack(self, ls):
        return ''.join(ls)
    
    def unpack(self, s):
        return list(s)


@strategy_for_instances(dict)
class FixedKeysDictStrategy(SearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor,
                    **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor,**kwargs)
        self.strategy_dict = {}
        for k, v in descriptor.items():
            self.strategy_dict[k] = strategies.strategy(v)

    def produce(self,size):
        result = {}
        for k,g in self.strategy_dict.items():
            result[k] = g.produce(size / len(self.strategy_dict))
        return result

    def complexity(self,x):
        return sum((v.complexity(x[k]) for k,v in self.strategy_dict))

    def simplify(self,x):
        for k,v in x.items():
            for s in self.strategy_dict[k].simplify(v):
                y = dict(x)
                y[k] = s
                yield y
