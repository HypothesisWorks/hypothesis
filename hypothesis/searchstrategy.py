from hypothesis.specmapper import SpecificationMapper
from hypothesis.tracker import Tracker
from hypothesis.flags import Flags

from inspect import isclass
from collections import namedtuple
from abc import abstractmethod
from math import log, log1p
import math

from random import random as rand, choice
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
    def strategy(self, descriptor, **kwargs):
        return self.specification_for(descriptor, **kwargs)

    def missing_specification(self, descriptor):
        if isinstance(descriptor, SearchStrategy):
            return descriptor
        else:
            return SpecificationMapper.missing_specification(self, descriptor)


def nice_string(xs, history=None):
    history = history or []
    if xs in history:
        return '(...)'
    history = history + [xs]
    recurse = lambda t: nice_string(t, history)
    if isinstance(xs, list):
        return '[' + ', '.join(map(recurse, xs)) + ']'
    if isinstance(xs, tuple):
        return '(' + ', '.join(map(recurse, xs)) + ')'
    if isinstance(xs, dict):
        return '{' + ', '.join(
            repr(k1) + ':' + recurse(v1)
            for k1, v1 in xs.items()
        ) + '}'
    try:
        return xs.__name__
    except AttributeError:
        pass

    try:
        d = xs.__dict__
    except AttributeError:
        return repr(xs)

    return "%s(%s)" % (
        xs.__class__.__name__,
        ', '.join(
            "%s=%s" % (k2, nice_string(v2, history)) for k2, v2 in d.items()
        )
    )


class SearchStrategy(object):
    def __init__(self,
                 strategies,
                 descriptor):
        self.descriptor = descriptor
        strategies.cache_specification_for_descriptor(descriptor, self)

    def __repr__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            nice_string(self.descriptor)
        )

    def may_call_self_recursively(self):
        if not hasattr(self, '__may_call_self_recursively'):
            self.__may_call_self_recursively = any(
                self is x for x in self.all_child_strategies()
            )
        return self.__may_call_self_recursively

    def all_child_strategies(self):
        stack = [self]
        seen = []

        while stack:
            head = stack.pop()
            for c in head.child_strategies():
                if any((s is c for s in seen)):
                    continue
                yield c
                stack.append(c)
                seen.append(c)

    def flags(self):
        r = set()
        self.add_flags_to(r)
        return Flags(r)

    def personal_flag(self, flag):
        return (self, str(flag))

    def add_flags_to(self, s, history=None):
        history = history or []
        if self in history:
            return
        history.append(self)
        for f in self.own_flags():
            s.add(f)
        for c in self.child_strategies():
            c.add_flags_to(s, history)

    def own_flags(self):
        return ()

    def child_strategies(self):
        return ()

    @abstractmethod
    def produce(self, size, flags):
        pass  # pragma: no coverass  # pragma: no cover

    def complexity(self, value):
        return 0

    def simplify(self, value):
        return iter(())

    def simplify_such_that(self, t, f):
        tracker = Tracker()
        yield t

        while True:
            for s in self.simplify(t):
                if tracker.track(s) > 1:
                    continue
                if f(s):
                    yield s
                    t = s
                    break
            else:
                break

    def could_have_produced(self, x):
        d = self.descriptor
        c = d if isclass(d) else d.__class__
        return isinstance(x, c)

entropy_to_geom_cache = {}


def geometric_probability_for_entropy(desired_entropy):
    if desired_entropy <= 1e-8:
        return 0.0

    if desired_entropy in entropy_to_geom_cache:
        return entropy_to_geom_cache[desired_entropy]

    def h(p):
        q = 1 - p
        return -(q * log1p(-p) + p * log(p))/(log(2) * p)

    lower = 0.0
    upper = 1.0
    for _ in xrange(max(int(desired_entropy * 2), 64)):
        mid = (lower + upper) / 2
        if h(mid) > desired_entropy:
            lower = mid
        else:
            upper = mid

    entropy_to_geom_cache[desired_entropy] = mid
    return mid


def arbitrary_int():
    return random.randint(-2**32, 2**32)


def geometric_int(p):
    if p <= 0:
        return arbitrary_int()
    elif p >= 1:
        return 0
    denom = log1p(- p)
    return int(log(rand()) / denom)


@strategy_for(int)
class IntStrategy(SearchStrategy):
    def own_flags(self):
        return ("allow_negative_ints",)

    def complexity(self, value):
        if value >= 0:
            return value
        else:
            return 1 - value

    def produce(self, size, flags):
        can_be_negative = flags.enabled("allow_negative_ints") and size > 1

        if size <= 1e-8:
            return 0

        if size >= 32:
            return arbitrary_int()

        if can_be_negative:
            size -= 1

        p = geometric_probability_for_entropy(size)
        n = geometric_int(p)
        if can_be_negative and rand() <= 0.5:
            n = -n
        return n

    def simplify(self, x):
        if x < 0:
            yield -x
            for y in self.simplify(-x):
                yield -y
        elif x > 0:
            #FIXME: This is a stupid way to do it
            seen = {0}
            yield 0
            max_not_seen = x - 1
            while max_not_seen > 0:
                n = random.randint(0, max_not_seen)
                if n not in seen:
                    seen.add(n)
                    if n == max_not_seen:
                        while max_not_seen in seen:
                            max_not_seen -= 1
                    yield n


@strategy_for(float)
class FloatStrategy(SearchStrategy):
    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.int_strategy = strategies.strategy(int)

    def own_flags(self):
        return ("allow_negative_floats",)

    def produce(self, size, flags):
        if flags.enabled("allow_negative_floats"):
            s2 = math.exp(2 * size) / (2 * math.pi * math.e)
            return random.gauss(0, s2)
        else:
            return random.expovariate(math.exp(1 - size))

    def complexity(self, x):
        return x if x >= 0 else 1 - x

    def simplify(self, x):
        if x < 0:
            yield -x

        n = int(x)
        y = float(n)
        if x != y: yield y
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

    def produce(self, size,flags):
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

    def child_strategies(self):
        return self.element_strategies

    def could_have_produced(self,xs):
        if not SearchStrategy.could_have_produced(self,xs): return False
        if len(xs) != len(self.element_strategies): return False
        return all((s.could_have_produced(x) for s,x in zip(self.element_strategies, xs)))

    def complexity(self, xs):
        return sum((s.complexity(x) for s,x in zip(self.element_strategies, xs)))

    def newtuple(self, xs):
        if self.descriptor.__class__ == tuple:
            return tuple(xs)
        else:
            return self.descriptor.__class__(*xs)

    def produce(self, size, flags):
        es = self.element_strategies
        return self.newtuple([g.produce(float(size)/len(es),flags) for g in es])

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
                yield self.newtuple(z)
        for i in xrange(0, len(x)):
            for j in xrange(0, len(x)):
                if i == j: continue
                for s in self.element_strategies[i].simplify(x[i]):
                    for t in self.element_strategies[j].simplify(x[j]):
                        z = list(x)
                        z[i] = s
                        z[j] = t
                        yield self.newtuple(z)


@strategy_for_instances(list)
class ListStrategy(SearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor,
                    **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor,**kwargs)

        self.element_strategy = strategies.strategy(one_of(descriptor))

    def own_flags(self):
        return ('allow_empty_lists',)

    def child_strategies(self):
        return (self.element_strategy,)

    def entropy_allocated_for_length(self, size):
        if size <= 2: return 0.5 * size;
        else: return min(0.05 * (size - 2.0) + 2.0, 6)

    def produce(self, size, flags):
        le = self.entropy_allocated_for_length(size)
        lp = geometric_probability_for_entropy(le)
        length = geometric_int(lp)
        empty_allowed = self.may_call_self_recursively() or flags.enabled('allow_empty_lists')
        if not empty_allowed:
            length += 1

        if length == 0:
            return []
        multiplier = 1.0/(1.0 - lp) if empty_allowed else 1.0
        element_entropy = multiplier * (size - le) / length
        return [self.element_strategy.produce(element_entropy,flags) for _ in xrange(length)]

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
        pass  # pragma: no cover

    @abstractmethod
    def unpack(self, x):
        pass  # pragma: no cover

    def child_strategies(self):
        return (self.mapped_strategy,)

    def produce(self, size, flags):
        return self.pack(self.mapped_strategy.produce(size,flags))

    def complexity(self, x):
        return self.mapped_strategy.complexity(self.unpack(x))

    def simplify(self, x):
        for y in self.mapped_strategy.simplify(self.unpack(x)):
            yield self.pack(y)


@strategy_for(complex)
class ComplexStrategy(MappedSearchStrategy):
    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.mapped_strategy = strategies.strategy((float, float))

    def pack(self, x):
        return complex(*x)

    def unpack(self, x):
        return (x.real, x.imag)


@strategy_for_instances(set)
class SetStrategy(MappedSearchStrategy):
    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.mapped_strategy = strategies.strategy(list(descriptor))

    def pack(self, x):
        return set(x)

    def unpack(self, x):
        return list(x)


class OneCharStringStrategy(SearchStrategy):
    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.characters = kwargs.get('characters', map(chr, range(0, 127)))
        self.zero_point = ord(kwargs.get('zero_point', '0'))

    def produce(self, size, flags):
        return choice(self.characters)

    def complexity(self, x):
        return abs(ord(x) - self.zero_point)

    def simplify(self, x):
        c = ord(x)
        if c < self.zero_point:
            yield chr(2 * self.zero_point - c)
            for d in xrange(c+1, self.zero_point + 1):
                yield chr(d)
        elif c > self.zero_point:
            for d in xrange(c - 1, self.zero_point - 1, -1):
                yield chr(d)


@strategy_for(str)
class StringStrategy(MappedSearchStrategy):
    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
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
    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.strategy_dict = {}
        for k, v in descriptor.items():
            self.strategy_dict[k] = strategies.strategy(v)

    def child_strategies(self):
        return self.strategy_dict.values()

    def produce(self, size, flags):
        result = {}
        for k, g in self.strategy_dict.items():
            result[k] = g.produce(size / len(self.strategy_dict), flags)
        return result

    def complexity(self, x):
        return sum((v.complexity(x[k]) for k, v in self.strategy_dict.items()))

    def simplify(self, x):
        for k, v in x.items():
            for s in self.strategy_dict[k].simplify(v):
                y = dict(x)
                y[k] = s
                yield y

OneOf = namedtuple('OneOf', 'elements')

def one_of(args):
    args = list(args)
    if not args:
        raise ValueError("one_of requires at least one value to choose from")
    if len(args) == 1:
        return args[0]
    return OneOf(args)

@strategy_for_instances(OneOf)
class OneOfStrategy(SearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor,
                    **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor,**kwargs)
        self.element_strategies = [strategies.strategy(x) for x in descriptor.elements]

    def own_flags(self):
        return tuple((self.personal_flag(d) for d in self.descriptor.elements))

    def child_strategies(self):
        return self.element_strategies

    def could_have_produced(self, x):
        return any((s.could_have_produced(x) for s in self.element_strategies))

    def how_many_elements_to_pick(self, size):
        max_entropy_to_use = size / 2
        n = len(self.element_strategies)
        if max_entropy_to_use >= log(n, 2):
            return n
        else:
            return int(2 ** max_entropy_to_use)

    def produce(self, size, flags):
        def enabled(c):
            return flags.enabled(self.personal_flag(c.descriptor))
        enabled_strategies = [
            es for es in self.element_strategies if enabled(es)
        ]
        enabled_strategies = enabled_strategies or self.element_strategies
        m = min(self.how_many_elements_to_pick(size), len(enabled_strategies))
        size -= log(m, 2)
        return choice(enabled_strategies[0:m]).produce(size, flags)

    def find_first_strategy(self, x):
        for s in self.element_strategies:
            if s.could_have_produced(x):
                return s
        else:
            raise ValueError(
                "Value %s could not have been produced from %s" % (x, self)
            )

    def complexity(self, x):
        return self.find_first_strategy(x).complexity(x)

    def simplify(self, x):
        return self.find_first_strategy(x).simplify(x)


Just = namedtuple('Just', 'value')
just = Just

@strategy_for_instances(Just)
class JustStrategy(SearchStrategy):
    def produce(self, size, flags):
        return self.descriptor.value
