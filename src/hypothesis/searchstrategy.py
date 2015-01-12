from hypothesis.internal.tracker import Tracker
import hypothesis.params as params
import hypothesis.internal.utils.distributions as dist

import inspect
from abc import abstractmethod
from six.moves import xrange
from six import text_type, binary_type, integer_types
import string
import random as r
import hypothesis.descriptors as descriptors
from copy import deepcopy


def mix_generators(*generators):
    generators = list(generators)
    while generators:
        for i in xrange(len(generators)):
            try:
                yield next(generators[i])
            except StopIteration:
                generators[i] = None
        generators = [x for x in generators if x is not None]


def nice_string(xs):
    if isinstance(xs, list):
        return '[' + ', '.join(map(nice_string, xs)) + ']'
    if type(xs) == tuple:
        if len(xs) == 1:
            return '(%s,)' % (nice_string(xs[0]),)
        else:
            return '(' + ', '.join(map(nice_string, xs)) + ')'
    if isinstance(xs, dict):
        return '{' + ', '.join(
            repr(k1) + ':' + nice_string(v1)
            for k1, v1 in xs.items()
        ) + '}'
    if isinstance(xs, set):
        return '{%s}' % (
            ', '.join(
                map(nice_string, xs)
            )
        )
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
            '%s=%s' % (k2, nice_string(v2)) for k2, v2 in d.items()
        )
    )


class SearchStrategy(object):
    has_immutable_data = True

    def __repr__(self):
        return '%s(%s)' % (
            self.__class__.__name__,
            nice_string(self.descriptor)
        )

    def __init__(self):
        pass

    @abstractmethod
    def produce(self, random, parameter_value):
        pass  # pragma: no cover

    def copy(self, value):
        if self.has_immutable_data:
            return value
        else:
            return deepcopy(value)

    def simplify(self, value):
        return iter(())

    def simplify_such_that(self, t, f):
        if not f(t):
            raise ValueError(
                "%r does not satisfy predicate %s" % (t, f))
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

    def __or__(self, other):
        if not isinstance(other, SearchStrategy):
            raise ValueError("Cannot | a SearchStrategy with %r" % (other,))
        return one_of_strategies((self, other))


class IntStrategy(SearchStrategy):
    descriptor = int

    def could_have_produced(self, x):
        return isinstance(x, integer_types)

    def simplify(self, x):
        if x < 0:
            yield -x
            for y in self.simplify(-x):
                yield -y
        elif x > 0:
            yield 0
            yield x // 2
            max_iters = 100
            if x <= max_iters:
                for i in xrange(x - 1, 0, -1):
                    yield i
            else:
                random = r.Random(x)
                seen = {0, x // 2}
                for _ in xrange(max_iters):
                    i = random.randint(0, x - 1)
                    if i not in seen:
                        yield i
                    seen.add(i)


class RandomGeometricIntStrategy(IntStrategy):
    parameter = params.CompositeParameter(
        negative_probability=params.BetaFloatParameter(0.5, 0.5),
        p=params.BetaFloatParameter(alpha=0.2, beta=1.8),
    )

    def produce(self, random, parameter):
        value = dist.geometric(random, parameter.p)
        if (
            dist.biased_coin(random, parameter.negative_probability)
        ):
            value = -value
        return value


class BoundedIntStrategy(SearchStrategy):
    descriptor = int
    parameter = params.CompositeParameter()

    def __init__(self, start, end):
        self.start = start
        self.end = end
        if start > end:
            raise ValueError("Invalid range [%d, %d]" % (start, end))
        self.parameter = params.NonEmptySubset(
            tuple(range(start, end + 1)),
            activation_chance=min(0.5, 3.0 / (end - start + 1))
        )

    def produce(self, random, parameter):
        if self.start == self.end:
            return self.start
        return random.choice(parameter)

    def simplify(self, x):
        if x == self.start:
            return
        for t in xrange(x - 1, self.start - 1, -1):
            yield t
        mid = (self.start + self.end) // 2
        if x > mid:
            yield self.start + (self.end - x)
            for t in xrange(x + 1, self.end + 1):
                yield t


class FloatStrategy(SearchStrategy):
    descriptor = float

    def __init__(self):
        SearchStrategy.__init__(self)
        self.int_strategy = IntStrategy()

    def simplify(self, x):
        if x < 0:
            yield -x

        n = int(x)
        y = float(n)
        if x != y:
            yield y
        for m in self.int_strategy.simplify(n):
            yield x + (m - n)


class FixedBoundedFloatStrategy(SearchStrategy):
    descriptor = float

    parameter = params.CompositeParameter(
        p=params.UniformFloatParameter(0, 1),
        n=params.ExponentialParameter(0.5),
    )

    def __init__(self, lower_bound, upper_bound):
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

    def produce(self, random, pv):
        alpha = pv.p * pv.n
        beta = (1 - pv.p) * pv.n
        result = self.lower_bound + (
            self.upper_bound - self.lower_bound
        ) * random.betavariate(alpha, beta)
        return result

    def simplify(self, value):
        yield self.lower_bound
        yield self.upper_bound
        yield (self.lower_bound + self.upper_bound) * 0.5


class BoundedFloatStrategy(FloatStrategy):
    def __init__(self):
        super(BoundedFloatStrategy, self).__init__()
        self.inner_strategy = FixedBoundedFloatStrategy(0, 1)
        self.parameter = params.CompositeParameter(
            left=params.NormalParameter(0, 1),
            length=params.ExponentialParameter(1),
            spread=self.inner_strategy.parameter,
        )

    def produce(self, random, pv):
        return pv.left + self.inner_strategy.produce(
            random,  pv.spread
        ) * pv.length


class GaussianFloatStrategy(FloatStrategy):
    parameter = params.CompositeParameter(
        mean=params.NormalParameter(0, 1),
    )

    def produce(self, random, pv):
        return random.normalvariate(pv.mean, 1)


class ExponentialFloatStrategy(FloatStrategy):
    parameter = params.CompositeParameter(
        lambd=params.GammaParameter(2, 50),
        zero_point=params.NormalParameter(0, 1),
        negative=params.BiasedCoin(0.5),
    )

    def produce(self, random, pv):
        value = random.expovariate(pv.lambd)
        if pv.negative:
            value = -value
        return pv.zero_point + value


class BoolStrategy(SearchStrategy):
    descriptor = bool

    parameter = params.UniformFloatParameter(0, 1)

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
        self.has_immutable_data = all(s.has_immutable_data for s in strategies)

    def could_have_produced(self, xs):
        if xs.__class__ != self.tuple_type:
            return False
        if len(xs) != len(self.element_strategies):
            return False
        return all((s.could_have_produced(x)
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
    result.sort(key=repr)
    return result


class ListStrategy(SearchStrategy):
    has_immutable_data = False

    def __init__(self,
                 strategies, average_length=100.0):
        SearchStrategy.__init__(self)

        self.descriptor = _unique(x.descriptor for x in strategies)
        self.element_strategy = one_of_strategies(strategies)
        self.parameter = params.CompositeParameter(
            average_length=params.ExponentialParameter(1.0 / average_length),
            child_parameter=self.element_strategy.parameter,
        )

    def produce(self, random, pv):
        length = dist.geometric(random, 1.0 / (1 + pv.average_length))
        result = []
        for _ in xrange(length):
            result.append(
                self.element_strategy.produce(random, pv.child_parameter))
        return result

    def simplify(self, x):
        if not x:
            return iter(())
        generators = []

        generators.append(iter(([],)))

        indices = xrange(0, len(x))

        generators.append(
            [x[i]] for i in indices
        )

        def with_one_index_deleted():
            for i in indices:
                y = list(x)
                del y[i]
                yield y

        def with_one_index_simplified():
            for i in indices:
                for s in self.element_strategy.simplify(x[i]):
                    z = list(x)
                    z[i] = s
                    yield z

        if len(x) > 2:
            generators.append(with_one_index_deleted())

        generators.append(with_one_index_simplified())

        def with_two_indices_deleted():
            for i in xrange(0, len(x) - 1):
                for j in xrange(i, len(x) - 1):
                    y = list(x)
                    del y[i]
                    del y[j]
                    yield y

        if len(x) > 3:
            generators.append(with_two_indices_deleted())

        return mix_generators(*generators)


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

    def simplify(self, x):
        unpacked = self.unpack(x)
        for y in self.mapped_strategy.simplify(unpacked):
            yield self.pack(y)


class ComplexStrategy(SearchStrategy):
    descriptor = complex

    def __init__(self, float_strategy):
        super(ComplexStrategy, self).__init__()
        self.parameter = params.CompositeParameter(
            real=float_strategy.parameter,
            imaginary=float_strategy.parameter,
        )
        self.float_strategy = float_strategy

    def produce(self, random, pv):
        return complex(
            self.float_strategy.produce(random, pv.real),
            self.float_strategy.produce(random, pv.imaginary),
        )

    def simplify(self, x):
        if x.imag != 0:
            yield complex(x.real, 0)
        if x.real != 0:
            yield complex(0, x.imag)
        for t in self.float_strategy.simplify(x.real):
            yield complex(t, x.imag)
        for t in self.float_strategy.simplify(x.imag):
            yield complex(x.real, t)


class SetStrategy(MappedSearchStrategy):
    has_immutable_data = False

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

    def simplify(self, x):
        for i in xrange(self.characters.index(x), -1, -1):
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
        return binary_type(bytearray(x))

    def unpack(self, x):
        return list(bytearray(x))


class FixedKeysDictStrategy(SearchStrategy):
    has_immutable_data = False

    def __init__(self, strategy_dict):
        SearchStrategy.__init__(self)
        self.strategy_dict = dict(strategy_dict)
        self.parameter = params.DictParameter({
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
            result[k] = g.produce(random, pv[k])
        return result

    def simplify(self, x):
        for k, v in x.items():
            for s in self.strategy_dict[k].simplify(v):
                y = dict(x)
                y[k] = s
                yield y


class OneOfStrategy(SearchStrategy):

    def __init__(self,
                 strategies):
        super(OneOfStrategy, self).__init__()
        flattened_strategies = []
        for s in strategies:
            if isinstance(s, OneOfStrategy):
                flattened_strategies += s.element_strategies
            else:
                flattened_strategies.append(s)
        strategies = tuple(flattened_strategies)
        if len(strategies) <= 1:
            raise ValueError("Need at least 2 strategies to choose amongst")
        descriptor = descriptors.one_of(
            _unique(s.descriptor for s in strategies))
        self.descriptor = descriptor
        self.element_strategies = list(strategies)
        n = len(self.element_strategies)
        self.parameter = params.CompositeParameter(
            enabled_children=params.NonEmptySubset(range(n)),
            child_parameters=params.CompositeParameter(
                e.parameter for e in self.element_strategies
            )
        )
        self.has_immutable_data = all(
            s.has_immutable_data for s in self.element_strategies)

    def could_have_produced(self, x):
        return any((s.could_have_produced(x) for s in self.element_strategies))

    def produce(self, random, pv):
        if len(pv.enabled_children) == 1:
            child = pv.enabled_children[0]
        else:
            child = pv.enabled_children[
                random.randint(0, len(pv.enabled_children) - 1)]
        return self.element_strategies[child].produce(
            random, pv.child_parameters[child])

    def simplify(self, x):
        t = Tracker()
        for cs in self.element_strategies:
            if cs.could_have_produced(x):
                for y in cs.simplify(x):
                    if t.track(y) == 1:
                        yield y


class JustStrategy(SearchStrategy):
    # We could do better here but it's probably not worth it
    # deepcopy has optimisations that will probably work just as well as
    # our check
    has_immutable_data = False

    def __init__(self, value):
        self.descriptor = descriptors.Just(value)

    parameter = params.CompositeParameter()

    def produce(self, random, pv):
        return self.descriptor.value
