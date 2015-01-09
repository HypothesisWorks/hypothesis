from hypothesis.internal.tracker import Tracker
import hypothesis.internal.params as params
import hypothesis.internal.utils.distributions as dist

import inspect
from collections import namedtuple
from abc import abstractmethod
from six.moves import xrange
from six import text_type, binary_type
import string
import random as r


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
    def __init__(self):
        pass

    def __repr__(self):
        return '%s(%s)' % (
            self.__class__.__name__,
            nice_string(self.descriptor)
        )

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
        c = d if inspect.isclass(d) else d.__class__
        return isinstance(x, c)


class IntStrategy(SearchStrategy):
    descriptor = int

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


class FloatStrategy(SearchStrategy):
    descriptor = float

    parameter = params.CompositeParameter(
        sign=params.UniformIntegerParameter(-1, 1),
        exponential_mean=params.GammaParameter(2, 50),
        gaussian_mean=params.NormalParameter(0, 1),
    )

    def __init__(self, int_strategy):
        SearchStrategy.__init__(self)
        self.int_strategy = int_strategy

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


class BoolStrategy(SearchStrategy):
    descriptor = bool

    parameter = params.UniformFloatParameter(0, 1)

    def complexity(self, x):
        if x:
            return 1
        else:
            return 0

    def produce(self, random, p):
        return dist.biased_coin(random, p)


class TupleStrategy(SearchStrategy):

    def __init__(self,
                 strategies, tuple_type):
        SearchStrategy.__init__(self)
        strategies = tuple(strategies)
        self.tuple_type = tuple_type
        self.descriptor = self.newtuple([s.descriptor for s in strategies])
        self.element_strategies = strategies
        self.parameter = params.CompositeParameter(
            x.parameter for x in self.element_strategies
        )

    def could_have_produced(self, xs):
        if not isinstance(xs, self.tuple_type):
            return False
        if len(xs) != len(self.element_strategies):
            return False
        return all((s.could_have_produced(x)
                    for s, x in zip(self.element_strategies, xs)))

    def complexity(self, xs):
        return sum((s.complexity(x)
                    for s, x in zip(self.element_strategies, xs)))

    def newtuple(self, xs):
        if self.tuple_type == tuple:
            return tuple(xs)
        else:
            return self.tuple_type(*xs)

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


def one_of_strategies(xs):
    xs = tuple(xs)
    if not xs:
        raise ValueError("Cannot join an empty list of strategies")
    if len(xs) == 1:
        return xs[0]
    return OneOfStrategy(xs)


def _unique(xs):
    result = []
    for x in xs:
        if x not in result:
            result.append(x)
    result.sort()
    return result


class ListStrategy(SearchStrategy):

    def __init__(self,
                 strategies):
        SearchStrategy.__init__(self)

        self.descriptor = _unique(x.descriptor for x in strategies)
        self.element_strategy = one_of_strategies(strategies)
        self.parameter = params.CompositeParameter(
            average_length=params.ExponentialParameter(50.0),
            child_parameter=self.element_strategy.parameter,
        )

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
    def __init__(self, descriptor, strategy):
        SearchStrategy.__init__(self)
        self.mapped_strategy = strategy
        self.descriptor = descriptor

    @property
    def parameter(self):
        return self.mapped_strategy.parameter

    @abstractmethod
    def pack(self, x):
        pass  # pragma: no cover

    @abstractmethod
    def unpack(self, x):
        pass  # pragma: no cover

    def produce(self, random, pv):
        return self.pack(self.mapped_strategy.produce(random, pv))

    def complexity(self, x):
        return self.mapped_strategy.complexity(self.unpack(x))

    def simplify(self, x):
        for y in self.mapped_strategy.simplify(self.unpack(x)):
            yield self.pack(y)


class ComplexStrategy(MappedSearchStrategy):

    def __init__(self, float_tuple_strategy):
        super(ComplexStrategy, self).__init__(
            strategy=float_tuple_strategy,
            descriptor=complex,
        )

    def pack(self, x):
        return complex(*x)

    def unpack(self, x):
        return (x.real, x.imag)


class SetStrategy(MappedSearchStrategy):

    def __init__(self, list_strategy):
        super(SetStrategy, self).__init__(
            strategy=list_strategy,
            descriptor=set(list_strategy.descriptor)
        )

    def pack(self, x):
        return set(x)

    def unpack(self, x):
        return list(x)


class OneCharStringStrategy(SearchStrategy):
    descriptor = text_type

    def __init__(self, characters=None):
        SearchStrategy.__init__(self)
        if characters is not None and not isinstance(characters, text_type):
            raise ValueError("Invalid characters %r: Not a %s" % (
                characters, text_type
            ))
        self.characters = characters or (
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


class StringStrategy(MappedSearchStrategy):
    def __init__(self, list_of_one_char_strings_strategy):
        return super(StringStrategy, self).__init__(
            descriptor=text_type,
            strategy=list_of_one_char_strings_strategy
        )

    def pack(self, ls):
        return text_type('').join(ls)

    def unpack(self, s):
        return list(s)


class BinaryStringStrategy(MappedSearchStrategy):
    def pack(self, x):
        return x.encode('utf-8')

    def unpack(self, x):
        return x.decode('utf-8')


class FixedKeysDictStrategy(SearchStrategy):

    def __init__(self, strategy_dict):
        SearchStrategy.__init__(self)
        self.strategy_dict = dict(strategy_dict)
        self.parameter = params.CompositeParameter(**{
            k: v.parameter
            for k, v
            in self.strategy_dict.items()
        })
        self.descriptor = {}
        for k, v in self.strategy_dict.items():
            self.descriptor[k] = v.descriptor

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


class OneOfStrategy(SearchStrategy):

    def __init__(self,
                 strategies):
        super(OneOfStrategy, self).__init__()
        strategies = tuple(strategies)
        if len(strategies) <= 1:
            raise ValueError("Need at least 2 strategies to choose amongst")
        descriptor = _unique(s.descriptor for s in strategies)
        if len(descriptor) == 1:
            descriptor = descriptor[0]
        else:
            descriptor = OneOf(descriptor)
        self.descriptor = descriptor
        self.element_strategies = list(strategies)
        n = len(self.element_strategies)
        self.parameter = params.CompositeParameter(
            enabled_children=params.NonEmptySubset(range(n)),
            child_parameters=params.CompositeParameter(
                e.parameter for e in self.element_strategies
            )
        )

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


class JustStrategy(SearchStrategy):
    def __init__(self, value):
        self.descriptor = Just(value)

    parameter = params.CompositeParameter()

    def produce(self, random, pv):
        return self.descriptor.value
