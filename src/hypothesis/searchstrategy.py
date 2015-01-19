"""Module defining SearchStrategy, which is the core type that Hypothesis uses
to explore data."""

from hypothesis.internal.tracker import Tracker
import hypothesis.params as params
import hypothesis.internal.utils.distributions as dist

import inspect
from abc import abstractmethod
from hypothesis.internal.compat import hrange
from hypothesis.internal.compat import text_type, binary_type, integer_types
import string
from random import Random
import hypothesis.descriptors as descriptors
from copy import deepcopy


def mix_generators(*generators):
    """Return a generator which cycles through these generator arguments.

    Will return all the same values as (x for g in generators for x in
    g) but will do so in an order that mixes the different generators
    up.

    """
    generators = list(generators)
    while generators:
        for i in hrange(len(generators)):
            try:
                yield next(generators[i])
            except StopIteration:
                generators[i] = None
        generators = [x for x in generators if x is not None]


def nice_string(xs):
    """Take a descriptor and produce a nicer string representation of it than
    repr.

    In particular this is designed to work around the problem that the
    repr for type objects is nasty.

    """
    # pylint: disable=too-many-return-statements
    if isinstance(xs, list):
        return '[' + ', '.join(map(nice_string, xs)) + ']'
    if type(xs) == tuple:
        if len(xs) == 1:
            return '(%s,)' % (nice_string(xs[0]),)
        else:
            return '(' + ', '.join(map(nice_string, xs)) + ')'
    if isinstance(xs, dict):
        return '{' + ', '.join(sorted([
            repr(k1) + ':' + nice_string(v1)
            for k1, v1 in xs.items()
        ])) + '}'
    if isinstance(xs, set):
        if not xs:
            return repr(xs)
        return '{%s}' % (
            ', '.join(
                sorted(map(nice_string, xs))
            )
        )
    if isinstance(xs, frozenset):
        if not xs:
            return repr(xs)
        return 'frozenset(%s)' % (nice_string(set(xs)),)
    try:
        return xs.__name__
    except AttributeError:
        pass

    if isinstance(xs, descriptors.Just):
        return repr(xs)

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

    """A SearchStrategy is an object that knows how to explore data of a given
    type.

    A search strategy's data production is defined by two distributions: The
    distribution if its parameter and the conditional distribution given a
    specific parameter value. In general the exact shapes of these should not
    be considered part of a class's contract and may change if a better choice
    is found. Generally the shape of the parameter is highly likely to change
    and the shape of the conditional distribution is quite likely to stay the
    same.

    """

    # A subclass should override this if its data is mutable and must be
    # copied before it is safe to pass to unknown functions.
    has_immutable_data = True

    # This should be an object that describes the type of data that this
    # SearchStrategy can produce.
    descriptor = None

    # This should be an object of type Parameter, values from which will be
    # passed to produce to control the shape of the distribution.
    parameter = None

    def __repr__(self):
        return '%s(%s)' % (
            self.__class__.__name__,
            nice_string(self.descriptor)
        )

    def __init__(self):
        pass

    def draw_and_produce(self, random):
        return self.produce(random, self.parameter.draw(random))

    @abstractmethod
    def produce(self, random, parameter_value):
        """Given a random number generator and a value drawn from
        self.parameter, produce a value matching this search strategy's
        descriptor."""
        pass  # pragma: no cover

    def copy(self, value):
        """Return a version of value such that if it is mutated this will not
        be reflected in value. If value is immutable it is perfectly acceptable
        to just return value itself.

        This version uses deepcopy and you can count on that remaining
        the case but subclasses should feel free to override it if
        providing copy hooks is not suitable for their needs.

        """
        if self.has_immutable_data:
            return value
        else:
            return deepcopy(value)

    def simplify(self, value):
        """Yield a number of values matching this descriptor that are in some
        sense "simpelr" than value. What simpler means is entirely up to
        subclasses and has no specified meaning. The intended interpretation is
        that if you are given a choice between value and an element of
        simplify(value) as an example you would rather one of the latter.

        While it is perfectly acceptable to have cycles in simplify where
        x{i+1} in simplify(xi) and x1 in simplify(x1) implementations should
        try to make a "best effort" attempt not to do this because it will tend
        to cause an unneccessarily large amount of time to be spent in
        simplification as it walks up and down the search space. However it is
        guaranteed to be safe and will not cause infinite loops.

        The results of this function should be a deterministic function of its
        input. If you want randomization, seed it off the value.

        """
        return iter(())

    def simplify_such_that(self, t, f):
        """Perform a greedy search to produce a "simplest" version of t that
        satisfies the predicate s. As each simpler version is found, yield it
        in turn. Stops when it has a value such that no value in simplify on
        the last value found satisfies f.

        Care is taken to avoid cycles in simplify.

        f should produce the same result deterministically. This function may
        raise an error given f such that f(t) returns False sometimes and True
        some other times.

        """
        assert self.could_have_produced(t)
        if not f(t):
            raise ValueError(
                '%r does not satisfy predicate %s' % (t, f))
        tracker = Tracker()
        yield t

        while True:
            for s in self.simplify(t):
                assert self.could_have_produced(s)
                if tracker.track(s) > 1:
                    continue
                if f(s):
                    yield s
                    t = s
                    break
            else:
                break

    def could_have_produced(self, x):
        """Is this a value that feasibly could have resulted from produce on
        this strategy.

        It is not strictly required that this method is accurate and the only
        invariant it *must* satisfy is that a value which returns True here
        will never error when passed to simplify, but implementations should
        try to make this as precise as possible as confusing behaviour may
        arise in some cases if it is not, with values produced by one strategy
        being passed to another for simplification when one_of is used.

        """
        d = self.descriptor
        c = d if inspect.isclass(d) else d.__class__
        return isinstance(x, c)

    def __or__(self, other):
        if not isinstance(other, SearchStrategy):
            raise ValueError('Cannot | a SearchStrategy with %r' % (other,))
        return one_of_strategies((self, other))


class IntStrategy(SearchStrategy):

    """A generic strategy for integer types that provides the basic methods
    other than produce.

    Subclasses should provide the produce method.

    """
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
                for i in hrange(x - 1, 0, -1):
                    yield i
            else:
                random = Random(x)
                seen = {0, x // 2}
                for _ in hrange(max_iters):
                    i = random.randint(0, x - 1)
                    if i not in seen:
                        yield i
                    seen.add(i)


class RandomGeometricIntStrategy(IntStrategy):

    """A strategy that produces integers whose magnitudes are a geometric
    distribution and whose sign is randomized with some probability.

    It will tend to be biased towards mostly negative or mostly
    positive, and the size of the integers tends to be biased towards
    the small.

    """
    parameter = params.CompositeParameter(
        negative_probability=params.BetaFloatParameter(0.5, 0.5),
        p=params.BetaFloatParameter(alpha=0.2, beta=1.8),
    )

    def produce(self, random, parameter):
        value = dist.geometric(random, parameter.p)
        if dist.biased_coin(random, parameter.negative_probability):
            value = -value
        return value


class BoundedIntStrategy(SearchStrategy):

    """A strategy for providing integers in some interval with inclusive
    endpoints."""

    descriptor = int
    parameter = params.CompositeParameter()

    def __init__(self, start, end):
        SearchStrategy.__init__(self)
        self.start = start
        self.end = end
        if start > end:
            raise ValueError('Invalid range [%d, %d]' % (start, end))
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
        for t in hrange(x - 1, self.start - 1, -1):
            yield t
        mid = (self.start + self.end) // 2
        if x > mid:
            yield self.start + (self.end - x)
            for t in hrange(x + 1, self.end + 1):
                yield t


class FloatStrategy(SearchStrategy):

    """Generic superclass for strategies which produce floats."""
    descriptor = float

    def __init__(self):
        SearchStrategy.__init__(self)
        self.int_strategy = RandomGeometricIntStrategy()

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

    """A strategy for floats distributed between two endpoints.

    The conditional distribution tries to produce values clustered
    closer to one of the ends.

    """
    descriptor = float

    parameter = params.CompositeParameter(
        cut=params.UniformFloatParameter(0, 1),
        leftwards=params.BiasedCoin(0.5),
    )

    def __init__(self, lower_bound, upper_bound):
        SearchStrategy.__init__(self)
        self.lower_bound = float(lower_bound)
        self.upper_bound = float(upper_bound)

    def produce(self, random, pv):
        if pv.leftwards:
            left = self.lower_bound
            right = pv.cut
        else:
            left = pv.cut
            right = self.upper_bound
        return left + random.random() * (right - left)

    def simplify(self, value):
        yield self.lower_bound
        yield self.upper_bound
        yield (self.lower_bound + self.upper_bound) * 0.5


class BoundedFloatStrategy(FloatStrategy):

    """A float strategy such that every conditional distribution is bounded but
    the endpoints may be arbitrary."""

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
            random, pv.spread
        ) * pv.length


class GaussianFloatStrategy(FloatStrategy):

    """A float strategy such that every conditional distribution is drawn from
    a gaussian."""
    parameter = params.CompositeParameter(
        mean=params.NormalParameter(0, 1),
    )

    def produce(self, random, pv):
        return random.normalvariate(pv.mean, 1)


class ExponentialFloatStrategy(FloatStrategy):

    """
    A float strategy such that every conditional distribution is of the form
    aX + b where a = +/- 1 and X is an exponentially distributed random
    variable.
    """
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

    """A strategy that produces Booleans with a Bernoulli conditional
    distribution."""
    descriptor = bool

    parameter = params.UniformFloatParameter(0, 1)

    def produce(self, random, p):
        return dist.biased_coin(random, p)


class TupleStrategy(SearchStrategy):

    """A strategy responsible for fixed length tuples based on heterogenous
    strategies for each of their elements.

    This also handles namedtuples

    """

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
        """Produce a new tuple of the correct type."""
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

        for i in hrange(0, len(x)):
            for s in self.element_strategies[i].simplify(x[i]):
                z = list(x)
                z[i] = s
                yield self.newtuple(z)
        for i in hrange(0, len(x)):
            for j in hrange(0, len(x)):
                if i == j:
                    continue
                for s in self.element_strategies[i].simplify(x[i]):
                    for t in self.element_strategies[j].simplify(x[j]):
                        z = list(x)
                        z[i] = s
                        z[j] = t
                        yield self.newtuple(z)


def one_of_strategies(xs):
    """Helper function for unioning multiple strategies."""
    xs = tuple(xs)
    if not xs:
        raise ValueError('Cannot join an empty list of strategies')
    if len(xs) == 1:
        return xs[0]
    return OneOfStrategy(xs)


def _unique(xs):
    """Helper function for removing duplicates from a list whilst preserving
    its order."""
    result = []
    for x in xs:
        if x not in result:
            result.append(x)
    result.sort(key=repr)
    return result


class ListStrategy(SearchStrategy):

    """A strategy for lists which takes an intended average length and a
    strategy for each of its element types and generates lists containing any
    of those element types.

    The conditional distribution of the length is geometric, and the
    conditional distribution of each parameter is whatever their
    strategies define.

    """
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
        for _ in hrange(length):
            result.append(
                self.element_strategy.produce(random, pv.child_parameter))
        return result

    def simplify(self, x):
        if not x:
            return iter(())
        generators = []

        generators.append(iter(([],)))

        indices = hrange(len(x) - 1, -1, -1)

        generators.append(
            [x[i]] for i in indices
        )

        def with_one_index_deleted():
            """yield lists that are the same as x but lacking a single
            element."""
            for i in indices:
                y = list(x)
                del y[i]
                yield y

        def with_one_index_simplified():
            """yield lists that are the same as x but with a single element
            simplified according to its defined strategy."""
            for i in indices:
                for s in self.element_strategy.simplify(x[i]):
                    z = list(x)
                    z[i] = s
                    yield z

        if len(x) > 2:
            generators.append(with_one_index_deleted())

        generators.append(with_one_index_simplified())

        def with_two_indices_deleted():
            """yield lists that are the same as x but lacking two elements."""
            for i in hrange(0, len(x) - 1):
                for j in hrange(i, len(x) - 1):
                    y = list(x)
                    del y[i]
                    del y[j]
                    yield y

        if len(x) > 3:
            generators.append(with_two_indices_deleted())

        return mix_generators(*generators)

    def could_have_produced(self, value):
        return isinstance(value, list) and all(
            self.element_strategy.could_have_produced(x)
            for x in value
        )


class MappedSearchStrategy(SearchStrategy):

    """A strategy which is defined purely by conversion to and from another
    strategy.

    Its parameter and distribution come from that other strategy.

    """

    def __init__(self, descriptor, strategy):
        SearchStrategy.__init__(self)
        self.mapped_strategy = strategy
        self.descriptor = descriptor
        self.parameter = self.mapped_strategy.parameter

    @abstractmethod
    def pack(self, x):
        """Take a value produced by the underlying mapped_strategy and turn it
        into a value suitable for outputting from this strategy."""
        pass  # pragma: no cover

    @abstractmethod
    def unpack(self, x):
        """Take a value produced from pack and convert it back to a value that
        could have been produced by the underlying strategy."""
        pass  # pragma: no cover

    def produce(self, random, pv):
        return self.pack(self.mapped_strategy.produce(random, pv))

    def could_have_produced(self, value):
        return super(MappedSearchStrategy, self).could_have_produced(
            value
        ) and self.mapped_strategy.could_have_produced(
            self.unpack(value)
        )

    def simplify(self, x):
        unpacked = self.unpack(x)
        for y in self.mapped_strategy.simplify(unpacked):
            yield self.pack(y)


class ComplexStrategy(SearchStrategy):

    """A strategy over complex numbers, with real and imaginary values
    distributed according to some provided strategy for floating point
    numbers."""
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

    """A strategy for sets of values, defined in terms of a strategy for lists
    of values."""
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


class FrozenSetStrategy(MappedSearchStrategy):

    """A strategy for frozensets of values, defined in terms of a strategy for
    lists of values."""

    def __init__(self, list_strategy):
        super(FrozenSetStrategy, self).__init__(
            strategy=list_strategy,
            descriptor=frozenset(list_strategy.descriptor)
        )
        self.has_immutable_data = (
            list_strategy.element_strategy.has_immutable_data
        )

    def pack(self, x):
        return frozenset(x)

    def unpack(self, x):
        return list(x)


class OneCharStringStrategy(SearchStrategy):

    """A strategy which generates single character strings of text type."""
    descriptor = text_type

    def __init__(self, characters=None):
        SearchStrategy.__init__(self)
        if characters is not None and not isinstance(characters, text_type):
            raise ValueError('Invalid characters %r: Not a %s' % (
                characters, text_type
            ))
        self.characters = characters or (
            text_type('0123456789') + text_type(string.ascii_letters))
        self.parameter = params.CompositeParameter()

    def produce(self, random, pv):
        return random.choice(self.characters)

    def simplify(self, x):
        for i in hrange(self.characters.index(x), -1, -1):
            yield self.characters[i]


class StringStrategy(MappedSearchStrategy):

    """A strategy for text strings, defined in terms of a strategy for lists of
    single character text strings."""

    def __init__(self, list_of_one_char_strings_strategy):
        super(StringStrategy, self).__init__(
            descriptor=text_type,
            strategy=list_of_one_char_strings_strategy
        )

    def pack(self, ls):
        return text_type('').join(ls)

    def unpack(self, s):
        return list(s)


class BinaryStringStrategy(MappedSearchStrategy):

    """A strategy for strings of bytes, defined in terms of a strategy for
    lists of bytes."""

    def pack(self, x):
        return binary_type(bytearray(x))

    def unpack(self, x):
        return list(bytearray(x))


class FixedKeysDictStrategy(SearchStrategy):

    """A strategy which produces dicts with a fixed set of keys, given a
    strategy for each of their equivalent values.

    e.g. {'foo' : some_int_strategy} would
    generate dicts with the single key 'foo' mapping to some integer.

    """
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

    """Implements a union of strategies. Given a number of strategies this
    generates values which could have come from any of them.

    The conditional distribution draws uniformly at random from some non-empty
    subset of these strategies and then draws from the conditional distribution
    of that strategy.

    Note: If two strategies both return could_have_produced(x) as True then
    when simplifying it is arbitrarily chosen which one gets passed x. The
    specific choice is an implementation detail that should not be relied upon.

    """

    def __init__(self,
                 strategies):
        SearchStrategy.__init__(self)
        flattened_strategies = []
        for s in strategies:
            if isinstance(s, OneOfStrategy):
                flattened_strategies += s.element_strategies
            else:
                flattened_strategies.append(s)
        strategies = tuple(flattened_strategies)
        if len(strategies) <= 1:
            raise ValueError('Need at least 2 strategies to choose amongst')
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

    """
    A strategy which simply returns a single fixed value with probability 1.
    """
    # We could do better here but it's probably not worth it
    # deepcopy has optimisations that will probably work just as well as
    # our check
    has_immutable_data = False

    def __init__(self, value):
        SearchStrategy.__init__(self)
        self.descriptor = descriptors.Just(value)

    def __repr__(self):
        return 'JustStrategy(value=%r)' % (self.descriptor.value,)

    parameter = params.CompositeParameter()

    def produce(self, random, pv):
        return self.descriptor.value

    def could_have_produced(self, value):
        return self.descriptor.value == value


class RandomWithSeed(Random):

    """A subclass of Random designed to expose the seed it was initially
    provided with.

    We consistently use this instead of Random objects because it makes
    examples much easier to recreate.

    """

    def __init__(self, seed):
        super(RandomWithSeed, self).__init__(seed)
        self.seed = seed

    def __repr__(self):
        return 'RandomWithSeed(%s)' % (self.seed,)

    def __copy__(self):
        r = RandomWithSeed(self.seed)
        r.setstate(self.getstate())
        return r

    def __deepcopy__(self, d):
        return self.__copy__()

    def __eq__(self, other):
        return self is other or (
            isinstance(other, RandomWithSeed) and
            self.seed == other.seed and
            self.getstate() == other.getstate()
        )


class RandomStrategy(SearchStrategy):

    """A strategy which produces Random objects.

    The conditional distribution is simply a RandomWithSeed seeded with
    a 128 bits of data chosen uniformly at random.

    """
    descriptor = Random
    parameter = params.CompositeParameter()
    has_immutable_data = False

    def produce(self, random, pv):
        return RandomWithSeed(random.getrandbits(128))

    def could_have_produced(self, value):
        return isinstance(value, RandomWithSeed)


class SampledFromStrategy(SearchStrategy):

    """A strategy which samples from a set of elements. This is essentially
    equivalent to using a OneOfStrategy over Just strategies but may be more
    efficient and convenient.

    The conditional distribution chooses uniformly at random from some
    non-empty subset of the elements.

    """

    def __init__(self, elements):
        SearchStrategy.__init__(self)
        self.elements = tuple(elements)
        self.descriptor = descriptors.SampledFrom(self.elements)
        self.parameter = params.NonEmptySubset(self.elements)

    def produce(self, random, pv):
        return random.choice(pv)

    def could_have_produced(self, value):
        return value in self.elements
