from hypothesis.produce import Producers
from hypothesis.simplify import DEFAULT_SIMPLIFIERS
from hypothesis.specmapper import SpecificationMapper
from hypothesis.tracker import Tracker
from inspect import isclass

from abc import abstractmethod
from math import log, log1p
import math

from random import random as rand,choice
import random

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
    def could_have_produced(self, x):
        d = self.descriptor
        c = d if isclass(d) else d.__class__
        return isinstance(x, c)

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

def geometric_int(p):
    denom = log1p(- p)
    if denom >= 0: return 0
    return int(log(rand()) / denom)

@strategy_for(int)
class IntStrategy(SearchStrategy):
    def complexity(self, value):
        if value >= 0: return value
        else: return 1 - value


    def produce(self,size):
        can_be_negative = size > 1
      
        if size <= 0:
            return 0
     
        if size >= 32:
            return random.randint(-2**32,2**32)

        if can_be_negative:
            size -= 1
        
        n = geometric_int(geometric_probability_for_entropy(size))
        if can_be_negative and rand() <= 0.5:
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

@strategy_for(float)
class FloatStrategy(SearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor,
                    **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor,**kwargs)
        self.int_strategy = strategies.strategy(int)

    def produce(self, size):
        s2 = math.exp(2 * size) / (2 * math.pi * math.e)
        return random.gauss(0, s2)

    def complexity(self, x):
        return x if x >= 0 else 1 - x
   
    def simplify(self, x):
        if x < 0: 
            yield -x

        n = int(x)
        yield float(n)
        for m in self.int_strategy.simplify(n):
            yield x + (m - n)

def h(p):
    return -(p * log(p) + (1-p) * log1p(-p))

def inverse_h(hd):
    if hd < 0: raise ValueError("Entropy h cannot be negative: %s" % h)
    if hd > 1: raise ValueError("Single bit entropy cannot be > 1: %s" % h)
    low = 0.0
    high = 0.5
    
    for _ in xrange(10):
        mid = (low + high) * 0.5
        if h(mid) < hd: low = mid
        else: high = mid

    return mid

@strategy_for(bool)
class BoolStrategy(SearchStrategy):
    def complexity(self,x):
        if x: return 1
        else: return 0
    
    def produce(self, size):
        if size >= 1: p = 0.5
        else: p = inverse_h(size)
        if rand() >= p: return False
        return True

@strategy_for_instances(tuple)
class TupleStrategy(SearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor,
                    **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor,**kwargs)
        self.element_strategies = tuple((strategies.strategy(x) for x in descriptor))

    def could_have_produced(self,xs):
        if not SearchStrategy.could_have_produced(self,xs): return False
        if len(xs) != len(self.element_strategies): return False
        return any((s.could_have_produced(x) for s,x in zipped(self.element_strategies, xs)))

    def complexity(self, xs):
        return sum((s.complexity(x) for s,x in zip(self.element_strategies, xs)))

    def produce(self, size):
        es = self.element_strategies
        return tuple([g.produce(float(size)/len(es)) for g in es])

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

    def entropy_allocated_for_length(self, size):
        if size <= 2: return 0.5 * size;
        else: return 0.05 * (size - 2.0) + 2.0

    def produce(self, size):
        le = self.entropy_allocated_for_length(size)
        lp = geometric_probability_for_entropy(le)
        length = geometric_int(lp)
        if length == 0:
            return []
        element_entropy = (size - le) / (length * (1.0 - lp))
        return [self.element_strategy.produce(element_entropy) for _ in xrange(length)]

    def simplify(self, x):
        indices = xrange(0, len(x)) 
        for i in indices:
            y = list(x)
            del y[i]
            yield y

        for i in indices:
            for s in self.element_strategy.simplify(x[i]):
                z = list(x)
                z[i] = s
                yield z 

        for i in xrange(0,len(x) - 1):
            for j in xrange(i,len(x) - 1):
                y = list(x)
                del y[i]
                del y[j]
                yield y

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
            yield self.pack(y)

@strategy_for_instances(set)
class SetStrategy(MappedSearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor,
                    **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor,**kwargs)
        self.mapped_strategy = strategies.strategy(list(descriptor))

    def pack(self, x):
        return set(x)

    def unpack(self, x):
        return list(x)

class OneCharStringStrategy(SearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor,
                    **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor,**kwargs)
        self.characters = kwargs.get('characters', map(chr,range(0,127)))
        self.zero_point = ord(kwargs.get('zero_point', '0'))

    def produce(self, size):
        return choice(self.characters)

    def complexity(self, x):
        return abs(ord(x) - self.zero_point)
        
    def simplify(self, x):
        c = ord(x)
        if c < self.zero_point:
            yield chr(2 * self.zero_point - c)
            for d in xrange(c+1, self.zero_point + 1): yield chr(d)
        elif c > self.zero_point:
            for d in xrange(c - 1, self.zero_point - 1, -1): yield chr(d)


@strategy_for(str)
class StringStrategy(MappedSearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor,
                    **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor,**kwargs)
        self.length_strategy = strategies.strategy(int)
        char_strategy = kwargs.get("char_strategy", 
                                   OneCharStringStrategy)
        
        cs = strategies.new_child_mapper()
        cs.define_specification_for(str, char_strategy)
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
