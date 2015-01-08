from hypothesis.internal.specmapper import SpecificationMapper
from hypothesis.internal.tracker import Tracker
import hypothesis.internal.params as params
import hypothesis.internal.utils.distributions as dist

from inspect import isclass
from collections import namedtuple
from abc import abstractmethod
from six.moves import xrange
from six import text_type, binary_type
import string
import random as r


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

    return '%s(%s)' % (
        xs.__class__.__name__,
        ', '.join(
            '%s=%s' % (k2, nice_string(v2, history)) for k2, v2 in d.items()
        )
    )


class SearchStrategy(object):

    def __init__(self,
                 strategies,
                 descriptor):
        self.descriptor = descriptor
        strategies.cache_specification_for_descriptor(descriptor, self)

    def __repr__(self):
        return '%s(%s)' % (
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

    def child_strategies(self):
        return ()

    @abstractmethod
    def produce(self, random, parameter_value):
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


@strategy_for(int)
class IntStrategy(SearchStrategy):
    parameter = params.CompositeParameter(
        may_be_negative=params.BiasedCoin(0.5),
        negative_probability=params.UniformFloatParameter(0, 1),
        p=params.UniformFloatParameter(0, 1),
    )

    def complexity(self, value):
        if value >= 0:
            return value
        else:
            return 1 - value

    def produce(self, random, parameter):
        value = dist.geometric(random, parameter.p)
        if (
            parameter.may_be_negative and
            dist.biased_coin(random, parameter.negative_probability)
        ):
            value = -value
        return value

    def simplify(self, x):
        if x < 0:
            yield -x
            for y in self.simplify(-x):
                yield -y
        elif x > 0:
            yield 0
            random = r.Random(x)
            values = list(xrange(1, x))
            random.shuffle(values)
            for v in values:
                yield v


@strategy_for(float)
class FloatStrategy(SearchStrategy):
    parameter = params.CompositeParameter(
        sign=params.UniformIntegerParameter(-1, 1),
        exponential_mean=params.GammaParameter(2, 50),
        gaussian_mean=params.NormalParameter(0, 1),
    )

    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.int_strategy = strategies.strategy(int)

    def produce(self, random, pv):
        if pv.sign:
            result = random.expovariate(1.0 / pv.exponential_mean)
            if pv.sign < 0:
                result = -result
            return result
        else:
            return random.normalvariate(pv.gaussian_mean, 1.0)

    def complexity(self, x):
        return x if x >= 0 else 1 - x

    def simplify(self, x):
        if x < 0:
            yield -x

        n = int(x)
        y = float(n)
        if x != y:
            yield y
        for m in self.int_strategy.simplify(n):
            yield x + (m - n)


@strategy_for(bool)
class BoolStrategy(SearchStrategy):

    parameter = params.UniformFloatParameter(0, 1)

    def complexity(self, x):
        if x:
            return 1
        else:
            return 0

    def produce(self, random, p):
        return dist.biased_coin(random, p)


@strategy_for_instances(tuple)
class TupleStrategy(SearchStrategy):

    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.element_strategies = tuple(
            (strategies.strategy(x) for x in descriptor))
        self.parameter = params.CompositeParameter(
            x.parameter for x in self.element_strategies
        )

    def child_strategies(self):
        return self.element_strategies

    def could_have_produced(self, xs):
        if not SearchStrategy.could_have_produced(self, xs):
            return False
        if len(xs) != len(self.element_strategies):
            return False
        return all((s.could_have_produced(x)
                    for s, x in zip(self.element_strategies, xs)))

    def complexity(self, xs):
        return sum((s.complexity(x)
                    for s, x in zip(self.element_strategies, xs)))

    def newtuple(self, xs):
        if self.descriptor.__class__ == tuple:
            return tuple(xs)
        else:
            return self.descriptor.__class__(*xs)

    def produce(self, random, pv):
        es = self.element_strategies
        return self.newtuple([
            g.produce(random, v)
            for g, v in zip(es, pv)
        ])

    def simplify(self, x):
        """
        Defined simplification for tuples: We don't change the length of the
        tuple we only try to simplify individual elements of it.
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
                if i == j:
                    continue
                for s in self.element_strategies[i].simplify(x[i]):
                    for t in self.element_strategies[j].simplify(x[j]):
                        z = list(x)
                        z[i] = s
                        z[j] = t
                        yield self.newtuple(z)


@strategy_for_instances(list)
class ListStrategy(SearchStrategy):

    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)

        self.element_strategy = strategies.strategy(one_of(descriptor))
        self.parameter = params.CompositeParameter(
            average_length=params.ExponentialParameter(50.0),
            child_parameter=self.element_strategy.parameter,
        )

    def child_strategies(self):
        return (self.element_strategy,)

    def entropy_allocated_for_length(self, size):
        if size <= 2:
            return 0.5 * size
        else:
            return min(0.05 * (size - 2.0) + 2.0, 6)

    def produce(self, random, pv):
        length = dist.geometric(random, 1.0 / (1 + pv.average_length))
        result = []
        for _ in xrange(length):
            result.append(
                self.element_strategy.produce(random, pv.child_parameter))
        return result

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

        for i in xrange(0, len(x) - 1):
            for j in xrange(i, len(x) - 1):
                y = list(x)
                del y[i]
                del y[j]
                yield y


class MappedSearchStrategy(SearchStrategy):
    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.mapped_strategy = strategies.strategy(self.base_descriptor)

    @property
    def parameter(self):
        return self.mapped_strategy.parameter

    @abstractmethod
    def pack(self, x):
        pass  # pragma: no cover

    @abstractmethod
    def unpack(self, x):
        pass  # pragma: no cover

    def child_strategies(self):
        return (self.mapped_strategy,)

    def produce(self, random, pv):
        return self.pack(self.mapped_strategy.produce(random, pv))

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
        self.base_descriptor = list(descriptor)
        super(SetStrategy, self).__init__(strategies, descriptor, **kwargs)

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
        self.characters = kwargs.get(
            "characters",
            text_type("0123456789") + text_type(string.ascii_letters))
        self.parameter = params.CompositeParameter()

    def produce(self, random, pv):
        return random.choice(self.characters)

    def complexity(self, x):
        result = self.characters.index(x)
        assert result >= 0
        return result

    def simplify(self, x):
        for i in xrange(self.complexity(x), -1, -1):
            yield self.characters[i]


@strategy_for(text_type)
class StringStrategy(MappedSearchStrategy):
    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        char_strategy = kwargs.get('char_strategy',
                                   OneCharStringStrategy)
        cs = strategies.new_child_mapper()
        cs.define_specification_for(str, char_strategy)
        self.mapped_strategy = cs.strategy([str])

    def pack(self, ls):
        return ''.join(ls)

    def unpack(self, s):
        return list(s)


@strategy_for(binary_type)
class BinaryStringStrategy(MappedSearchStrategy):
    base_descriptor = text_type

    def pack(self, x):
        return x.encode('utf-8')

    def unpack(self, x):
        return x.decode('utf-8')


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
        self.parameter = params.CompositeParameter(**{
            k: v.parameter
            for k, v
            in self.strategy_dict.items()
        })

    def child_strategies(self):
        return self.strategy_dict.values()

    def produce(self, random, pv):
        result = {}
        for k, g in self.strategy_dict.items():
            result[k] = g.produce(random, getattr(pv, k))
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
        raise ValueError('one_of requires at least one value to choose from')
    if len(args) == 1:
        return args[0]
    return OneOf(args)


@strategy_for_instances(OneOf)
class OneOfStrategy(SearchStrategy):

    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.element_strategies = [
            strategies.strategy(x) for x in descriptor.elements]
        n = len(self.element_strategies)
        self.parameter = params.CompositeParameter(
            enabled_children=params.NonEmptySubset(range(n)),
            child_parameters=params.CompositeParameter(
                e.parameter for e in self.element_strategies
            )
        )

    def child_strategies(self):
        return self.element_strategies

    def could_have_produced(self, x):
        return any((s.could_have_produced(x) for s in self.element_strategies))

    def produce(self, random, pv):
        child = random.choice(pv.enabled_children)
        return self.element_strategies[child].produce(
            random, pv.child_parameters[child])

    def find_first_strategy(self, x):
        for s in self.element_strategies:
            if s.could_have_produced(x):
                return s
        else:
            raise ValueError(
                'Value %s could not have been produced from %s' % (x, self)
            )

    def complexity(self, x):
        return self.find_first_strategy(x).complexity(x)

    def simplify(self, x):
        return self.find_first_strategy(x).simplify(x)


Just = namedtuple('Just', 'value')
just = Just


@strategy_for_instances(Just)
class JustStrategy(SearchStrategy):
    parameter = params.CompositeParameter()

    def produce(self, random, pv):
        return self.descriptor.value
