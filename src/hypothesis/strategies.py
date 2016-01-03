# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import math
import struct
from decimal import Decimal

from hypothesis.errors import InvalidArgument
from hypothesis.control import assume
from hypothesis.settings import Settings
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.internal.compat import ArgSpec, text_type, getargspec, \
    integer_types, float_to_decimal, unicode_safe_repr
from hypothesis.internal.reflection import proxies
from hypothesis.searchstrategy.reprwrapper import ReprWrapperStrategy

__all__ = [
    'just', 'one_of',
    'none',
    'choices',
    'booleans', 'integers', 'floats', 'complex_numbers', 'fractions',
    'decimals',
    'characters', 'text', 'binary',
    'tuples', 'lists', 'sets', 'frozensets',
    'dictionaries', 'fixed_dictionaries',
    'sampled_from',
    'builds',
    'randoms', 'random_module',
    'streaming', 'basic', 'recursive', 'composite',
]


class FloatKey(object):

    def __init__(self, f):
        self.value = float_to_int(f)

    def __eq__(self, other):
        return isinstance(other, FloatKey) and (
            other.value == self.value
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.value)


def convert_value(v):
    if isinstance(v, float):
        return FloatKey(v)
    return (type(v), v)


def cacheable(fn):
    import weakref

    cache = weakref.WeakValueDictionary()

    @proxies(fn)
    def cached_strategy(*args, **kwargs):
        kwargs_cache_key = set()
        try:
            for k, v in kwargs.items():
                kwargs_cache_key.add((k, convert_value(v)))
        except TypeError:
            return fn(*args, **kwargs)
        cache_key = (
            tuple(map(convert_value, args)), frozenset(kwargs_cache_key))
        try:
            return cache[cache_key]
        except TypeError:
            return fn(*args, **kwargs)
        except KeyError:
            result = fn(*args, **kwargs)
            cache[cache_key] = result
            return result
    return cached_strategy


def defines_strategy(strategy_definition):
    from hypothesis.searchstrategy.deferred import DeferredStrategy

    @proxies(strategy_definition)
    def accept(*args, **kwargs):
        return DeferredStrategy(strategy_definition, args, kwargs)
    return accept


def just(value):
    """Return a strategy which only generates value.

    Note: value is not copied. Be wary of using mutable values.

    """
    from hypothesis.searchstrategy.misc import JustStrategy

    def calc_repr():
        return u'just(%s)' % (unicode_safe_repr(value),)

    return ReprWrapperStrategy(JustStrategy(value), calc_repr)


@defines_strategy
def none():
    """Return a strategy which only generates None."""
    return just(None)


def one_of(arg, *args):
    """Return a strategy which generates values from any of the argument
    strategies."""

    if not args:
        check_strategy(arg)
        return arg
    from hypothesis.searchstrategy.strategies import OneOfStrategy
    args = (arg,) + args
    for arg in args:
        check_strategy(arg)
    return OneOfStrategy(args)


@cacheable
@defines_strategy
def integers(min_value=None, max_value=None):
    """Returns a strategy which generates integers (in Python 2 these may be
    ints or longs).

    If min_value is not None then all values will be >=
    min_value. If max_value is not None then all values will be <= max_value

    """

    check_valid_integer(min_value)
    check_valid_integer(max_value)
    check_valid_interval(min_value, max_value, u'min_value', u'max_value')

    from hypothesis.searchstrategy.numbers import IntegersFromStrategy, \
        BoundedIntStrategy, RandomGeometricIntStrategy, WideRangeIntStrategy

    if min_value is None:
        if max_value is None:
            return (
                RandomGeometricIntStrategy() |
                WideRangeIntStrategy()
            )
        else:
            return IntegersFromStrategy(0).map(lambda x: max_value - x)
    else:
        if max_value is None:
            return IntegersFromStrategy(min_value)
        else:
            if min_value == max_value:
                return just(min_value)
            return BoundedIntStrategy(min_value, max_value)


@cacheable
@defines_strategy
def booleans():
    """Returns a strategy which generates instances of bool."""
    from hypothesis.searchstrategy.misc import BoolStrategy
    return BoolStrategy()


def is_negative(x):
    return math.copysign(1, x) < 0


def count_between_floats(x, y):
    assert x <= y
    if is_negative(x):
        if is_negative(y):
            return float_to_int(x) - float_to_int(y) + 1
        else:
            return count_between_floats(x, -0.0) + count_between_floats(0.0, y)
    else:
        assert not is_negative(y)
        return float_to_int(y) - float_to_int(x) + 1


def float_to_int(value):
    return (
        struct.unpack(b'!Q', struct.pack(b'!d', value))[0]
    )


def int_to_float(value):
    return (
        struct.unpack(b'!d', struct.pack(b'!Q', value))[0]
    )


@cacheable
@defines_strategy
def floats(
    min_value=None, max_value=None, allow_nan=None, allow_infinity=None
):
    """Returns a strategy which generates floats.

    - If min_value is not None, all values will be >= min_value.
    - If max_value is not None, all values will be <= max_value.
    - If min_value or max_value is not None, it is an error to enable
      allow_nan.
    - If both min_value and max_value are not None, it is an error to enable
      allow_infinity.

    Where not explicitly ruled out by the bounds, all of infinity, -infinity
    and NaN are possible values generated by this strategy.

    """

    if allow_nan is None:
        allow_nan = bool(min_value is None and max_value is None)
    elif allow_nan:
        if min_value is not None or max_value is not None:
            raise InvalidArgument(
                u'Cannot have allow_nan=%r, with min_value or max_value' % (
                    allow_nan
                ))

    check_valid_bound(min_value, u'min_value')
    check_valid_bound(max_value, u'max_value')
    check_valid_interval(min_value, max_value, u'min_value', u'max_value')
    if min_value is not None:
        min_value = float(min_value)
    if max_value is not None:
        max_value = float(max_value)
    if min_value == float(u'-inf'):
        min_value = None
    if max_value == float(u'inf'):
        max_value = None

    if allow_infinity is None:
        allow_infinity = bool(min_value is None or max_value is None)
    elif allow_infinity:
        if min_value is not None and max_value is not None:
            raise InvalidArgument(
                u'Cannot have allow_infinity=%r, with both min_value and '
                u'max_value' % (
                    allow_infinity
                ))

    from hypothesis.searchstrategy.numbers import WrapperFloatStrategy, \
        GaussianFloatStrategy, BoundedFloatStrategy, ExponentialFloatStrategy,\
        JustIntFloats, NastyFloats, FullRangeFloats, \
        FixedBoundedFloatStrategy
    if min_value is None and max_value is None:
        return WrapperFloatStrategy(
            GaussianFloatStrategy() |
            BoundedFloatStrategy() |
            ExponentialFloatStrategy() |
            JustIntFloats() |
            NastyFloats(allow_nan, allow_infinity) |
            FullRangeFloats(allow_nan, allow_infinity)
        )
    elif min_value is not None and max_value is not None:
        if min_value == max_value:
            return just(min_value)
        elif math.isinf(max_value - min_value):
            assert min_value < 0 and max_value > 0
            return floats(min_value=0, max_value=max_value) | floats(
                min_value=min_value, max_value=0
            )
        elif count_between_floats(min_value, max_value) > 1000:
            critical_values = [
                min_value, max_value, min_value + (max_value - min_value) / 2]
            if min_value <= 0 <= max_value:
                if not is_negative(max_value):
                    critical_values.append(0.0)
                if is_negative(min_value):
                    critical_values.append(-0.0)
            return FixedBoundedFloatStrategy(
                lower_bound=min_value, upper_bound=max_value
            ) | sampled_from(critical_values)
        elif is_negative(max_value):
            assert is_negative(min_value)
            ub_int = float_to_int(max_value)
            lb_int = float_to_int(min_value)
            assert ub_int <= lb_int
            return integers(min_value=ub_int, max_value=lb_int).map(
                int_to_float
            )
        elif is_negative(min_value):
            return floats(min_value=min_value, max_value=-0.0) | floats(
                min_value=0, max_value=max_value
            )
        else:
            ub_int = float_to_int(max_value)
            lb_int = float_to_int(min_value)
            assert lb_int <= ub_int
            return integers(min_value=lb_int, max_value=ub_int).map(
                int_to_float
            )
    elif min_value is not None:
        critical_values = [min_value]
        if allow_infinity:
            critical_values.append(float(u'inf'))
        if is_negative(min_value):
            critical_values.append(-0.0)
        if min_value <= 0:
            critical_values.append(0.0)
        return (
            floats(allow_infinity=allow_infinity, allow_nan=False).map(
                lambda x: assume(not math.isnan(x)) and min_value + abs(x)
            )
        ) | sampled_from(critical_values)
    else:
        assert max_value is not None
        critical_values = [max_value]
        if allow_infinity:
            critical_values.append(float(u'-inf'))
        if max_value >= 0:
            critical_values.append(-0.0)
            if not is_negative(max_value):
                critical_values.append(0.0)
        return (
            floats(allow_infinity=allow_infinity, allow_nan=False).map(
                lambda x: assume(not math.isnan(x)) and max_value - abs(x)
            )
        ) | sampled_from(critical_values)


@cacheable
@defines_strategy
def complex_numbers():
    """Returns a strategy that generates complex numbers."""
    from hypothesis.searchstrategy.numbers import ComplexStrategy
    return ComplexStrategy(
        tuples(floats(), floats())
    )


@cacheable
@defines_strategy
def tuples(*args):
    """Return a strategy which generates a tuple of the same length as args by
    generating the value at index i from args[i].

    e.g. tuples(integers(), integers()) would generate a tuple of length
    two with both values an integer.

    """
    for arg in args:
        check_strategy(arg)
    from hypothesis.searchstrategy.collections import TupleStrategy
    return TupleStrategy(args, tuple)


@defines_strategy
def sampled_from(elements):
    """Returns a strategy which generates any value present in the iterable
    elements.

    Note that as with just, values will not be copied and thus you
    should be careful of using mutable data

    """

    from hypothesis.searchstrategy.misc import SampledFromStrategy, \
        JustStrategy
    elements = tuple(iter(elements))
    if not elements:
        raise InvalidArgument(
            u'sampled_from requires at least one value'
        )
    if len(elements) == 1:
        return JustStrategy(elements[0])
    else:
        return SampledFromStrategy(elements)


@cacheable
@defines_strategy
def lists(
    elements=None, min_size=None, average_size=None, max_size=None,
    unique_by=None, unique=False,
):
    """Returns a list containing values drawn from elements length in the
    interval [min_size, max_size] (no bounds in that direction if these are
    None). If max_size is 0 then elements may be None and only the empty list
    will be drawn.

    average_size may be used as a size hint to roughly control the size
    of list but it may not be the actual average of sizes you get, due
    to a variety of factors.

    If unique is True (or something that evaluates to True), we compare direct
    object equality, as if unique_by was `lambda x: x`. This comparison only
    works for hashable types.

    if unique_by is not None it must be a function returning a hashable type
    when given a value drawn from elements. The resulting list will satisfy the
    condition that for i != j, unique_by(result[i]) != unique_by(result[j]).

    """
    if unique:
        if unique_by is not None:
            raise InvalidArgument((
                u'cannot specify both unique and unique_by (you probably only '
                u'want to set unique_by)'
            ))
        else:
            unique_by = lambda x: x

    if unique_by is not None:
        from hypothesis.searchstrategy.collections import UniqueListStrategy
        if max_size == 0:
            return builds(list)
        check_strategy(elements)
        if min_size is not None and elements.template_upper_bound < min_size:
            raise InvalidArgument((
                u'Cannot generate unique lists of size %d from %r, which '
                u'contains no more than %d distinct values') % (
                    min_size, elements, elements.template_upper_bound,
            ))
        min_size = min_size or 0
        max_size = max_size or float(u'inf')
        max_size = min(max_size, elements.template_upper_bound)
        if average_size is None:
            if max_size < float(u'inf'):
                if max_size <= 5:
                    average_size = min_size + 0.75 * (max_size - min_size)
                else:
                    average_size = (max_size + min_size) / 2
            else:
                average_size = max(
                    Settings.default.average_list_length,
                    min_size * 2
                )
        check_valid_sizes(min_size, average_size, max_size)
        result = UniqueListStrategy(
            elements=elements,
            average_size=average_size,
            max_size=max_size,
            min_size=min_size,
            key=unique_by
        )
        return result

    check_valid_sizes(min_size, average_size, max_size)
    from hypothesis.searchstrategy.collections import ListStrategy, \
        SingleElementListStrategy
    if min_size is None:
        min_size = 0
    if average_size is None:
        if max_size is None:
            average_size = Settings.default.average_list_length
        else:
            average_size = (min_size + max_size) * 0.5

    if elements is None or (max_size is not None and max_size <= 0):
        if max_size is None or max_size > 0:
            raise InvalidArgument(
                u'Cannot create non-empty lists without an element type'
            )
        else:
            return ListStrategy(())
    else:
        check_strategy(elements)
        if elements.template_upper_bound == 1:
            from hypothesis.searchstrategy.numbers import IntegersFromStrategy
            if max_size is None:
                length_strat = IntegersFromStrategy(
                    min_size, average_size=average_size - min_size)
            else:
                length_strat = integers(min_size, max_size)
            return SingleElementListStrategy(elements, length_strat)
        return ListStrategy(
            (elements,), average_length=average_size,
            min_size=min_size, max_size=max_size,
        )


@cacheable
@defines_strategy
def sets(elements=None, min_size=None, average_size=None, max_size=None):
    """This has the same behaviour as lists, but returns sets instead.

    Note that Hypothesis cannot tell if values are drawn from elements
    are hashable until running the test, so you can define a strategy
    for sets of an unhashable type but it will fail at test time.

    """
    return lists(
        elements=elements, min_size=min_size, average_size=average_size,
        max_size=max_size, unique=True
    ).map(set)


@cacheable
@defines_strategy
def frozensets(elements=None, min_size=None, average_size=None, max_size=None):
    """This is identical to the sets function but instead returns
    frozensets."""
    return lists(
        elements=elements, min_size=min_size, average_size=average_size,
        max_size=max_size, unique=True
    ).map(frozenset)


@defines_strategy
def fixed_dictionaries(mapping):
    """Generate a dictionary of the same type as mapping with a fixed set of
    keys mapping to strategies. mapping must be a dict subclass.

    Generated values have all keys present in mapping, with the
    corresponding values drawn from mapping[key]. If mapping is an
    instance of OrderedDict the keys will also be in the same order,
    otherwise the order is arbitrary.

    """
    from hypothesis.searchstrategy.collections import FixedKeysDictStrategy
    check_type(dict, mapping)
    for v in mapping.values():
        check_type(SearchStrategy, v)
    return FixedKeysDictStrategy(mapping)


@cacheable
@defines_strategy
def dictionaries(
    keys, values, dict_class=dict,
    min_size=None, average_size=None, max_size=None
):
    """Generates dictionaries of type dict_class with keys drawn from the keys
    argument and values drawn from the values argument.

    The size parameters have the same interpretation as for lists.

    """
    check_valid_sizes(min_size, average_size, max_size)
    if max_size == 0:
        return fixed_dictionaries(dict_class())
    check_strategy(keys)
    check_strategy(values)

    if min_size is not None and min_size > keys.template_upper_bound:
        raise InvalidArgument((
            u'Cannot generate dictionaries of size %d with keys from %r, '
            u'which contains no more than %d distinct values') % (
                min_size, keys, keys.template_upper_bound,
        ))

    if max_size is None:
        max_size = keys.template_upper_bound
    else:
        max_size = min(max_size, keys.template_upper_bound)

    return lists(
        tuples(keys, values),
        min_size=min_size, average_size=average_size, max_size=max_size,
        unique_by=lambda x: x[0]
    ).map(dict_class)


@cacheable
@defines_strategy
def streaming(elements):
    """Generates an infinite stream of values where each value is drawn from
    elements.

    The result is iterable (the iterator will never terminate) and
    indexable.

    """
    check_strategy(elements)
    from hypothesis.searchstrategy.streams import StreamStrategy
    return StreamStrategy(elements)


@cacheable
@defines_strategy
def characters(whitelist_categories=None, blacklist_categories=None,
               blacklist_characters=None, min_codepoint=None,
               max_codepoint=None):
    """Generates unicode text type (unicode on python 2, str on python 3)
    characters following specified filtering rules.

    This strategy accepts lists of Unicode categories, characters of which
    should (`whitelist_categories`) or should not (`blacklist_categories`)
    be produced.

    Also there could be applied limitation by minimal and maximal produced
    code point of the characters.

    If you know what exactly characters you don't want to be produced,
    pass them with `blacklist_characters` argument.

    """
    from hypothesis.searchstrategy.strings import OneCharStringStrategy
    return OneCharStringStrategy(whitelist_categories=whitelist_categories,
                                 blacklist_categories=blacklist_categories,
                                 blacklist_characters=blacklist_characters,
                                 min_codepoint=min_codepoint,
                                 max_codepoint=max_codepoint)


@cacheable
@defines_strategy
def text(
    alphabet=None,
    min_size=None, average_size=None, max_size=None
):
    """Generates values of a unicode text type (unicode on python 2, str on
    python 3) with values drawn from alphabet, which should be an iterable of
    length one strings or a strategy generating such. If it is None it will
    default to generating the full unicode range. If it is an empty collection
    this will only generate empty strings.

    min_size, max_size and average_size have the usual interpretations.

    """
    from hypothesis.searchstrategy.strings import OneCharStringStrategy, \
        StringStrategy
    if alphabet is None:
        char_strategy = OneCharStringStrategy(blacklist_categories=['Cs'])
    elif not alphabet:
        if (min_size or 0) > 0:
            raise InvalidArgument(
                u'Invalid min_size %r > 0 for empty alphabet' % (
                    min_size,
                )
            )
        return just(u'')
    elif isinstance(alphabet, SearchStrategy):
        char_strategy = alphabet
    else:
        char_strategy = sampled_from(list(map(text_type, alphabet)))
    return StringStrategy(lists(
        char_strategy, average_size=average_size, min_size=min_size,
        max_size=max_size
    ))


@cacheable
@defines_strategy
def binary(
    min_size=None, average_size=None, max_size=None
):
    """Generates the appropriate binary type (str in python 2, bytes in python
    3).

    min_size, average_size and max_size have the usual interpretations.

    """
    from hypothesis.searchstrategy.strings import BinaryStringStrategy
    return BinaryStringStrategy(
        lists(
            integers(min_value=0, max_value=255),
            average_size=average_size, min_size=min_size, max_size=max_size
        )
    )


@defines_strategy
def basic(
    basic=None,
    generate_parameter=None, generate=None, simplify=None, copy=None
):
    """Provides a facility to write your own strategies with significantly less
    work.

    See documentation for more details.

    """
    from hypothesis.searchstrategy.basic import basic_strategy, BasicStrategy
    from copy import deepcopy
    if basic is not None:
        if isinstance(basic, type):
            basic = basic()
        check_type(BasicStrategy, basic)
        generate_parameter = generate_parameter or basic.generate_parameter
        generate = generate or basic.generate
        simplify = simplify or basic.simplify
        copy = copy or basic.copy
    return basic_strategy(
        parameter=generate_parameter,
        generate=generate, simplify=simplify, copy=copy or deepcopy
    )


@cacheable
@defines_strategy
def randoms():
    """Generates instances of Random (actually a Hypothesis specific
    RandomWithSeed class which displays what it was initially seeded with)"""
    from hypothesis.searchstrategy.misc import RandomStrategy
    return RandomStrategy(integers())


class RandomSeeder(object):

    def __init__(self, seed):
        self.seed = seed

    def __repr__(self):
        return 'random.seed(%r)' % (self.seed,)


@cacheable
@defines_strategy
def random_module():
    """If your code depends on the global random module then you need to use
    this.

    It will explicitly seed the random module at the start of your test
    so that tests are reproducible. The value it passes you is an opaque
    object whose only useful feature is that its repr displays the
    random seed. It is not itself a random number generator. If you want
    a random number generator you should use the randoms() strategy
    which will give you one.

    """
    from hypothesis.control import cleanup
    import random

    def seed_random(seed):
        state = random.getstate()
        random.seed(seed)
        cleanup(lambda: random.setstate(state))
        return RandomSeeder(seed)

    return shared(
        integers().map(seed_random),
        'hypothesis.strategies.random_module()',
    )


@cacheable
@defines_strategy
def fractions():
    """Generates instances of fractions.Fraction."""
    from fractions import Fraction
    return tuples(integers(), integers(min_value=1)).map(
        lambda t: Fraction(*t)
    )


@cacheable
@defines_strategy
def decimals():
    """Generates instances of decimals.Decimal."""
    return (
        floats().map(float_to_decimal) |
        fractions().map(
            lambda f: Decimal(f.numerator) / f.denominator
        )
    )


@cacheable
@defines_strategy
def builds(target, *args, **kwargs):
    """Generates values by drawing from args and kwargs and passing them to
    target in the appropriate argument position.

    e.g. builds(target,
    integers(), flag=booleans()) would draw an integer i and a boolean b and
    call target(i, flag=b).

    """
    return tuples(tuples(*args), fixed_dictionaries(kwargs)).map(
        lambda value: target(*value[0], **value[1])
    )


@defines_strategy
def recursive(base, extend, max_leaves=100):
    """
    base: A strategy to start from.

    extend: A function which takes a strategy and returns a new strategy.

    max_leaves: The maximum number of elements to be drawn from base on a given
    run.

    This returns a strategy S such that S = extend(base | S). That is, values
    maybe drawn from base, or from any strategy reachable by mixing
    applications of | and extend.

    An example may clarify: recursive(booleans(), lists) would return a
    strategy that may return arbitrarily nested and mixed lists of booleans.
    So e.g. False, [True], [False, []], [[[[True]]]], are all valid values to
    be drawn from that strategy.
    """

    check_strategy(base)
    extended = extend(base)
    if not isinstance(extended, SearchStrategy):
        raise InvalidArgument(
            u'Expected extend(%r) to be a SearchStrategy but got %r' % (
                base, extended
            ))
    from hypothesis.searchstrategy.recursive import RecursiveStrategy
    return RecursiveStrategy(base, extend, max_leaves)


@defines_strategy
def permutations(values):
    """Return a strategy which returns permutations of the collection
    "values"."""
    values = list(values)
    if not values:
        return just(()).map(lambda _: [])

    def build_permutation(swaps):
        initial = list(values)
        for i, j in swaps:
            initial[i], initial[j] = initial[j], initial[i]
        return initial
    n = len(values)
    index = integers(0, n - 1)
    return lists(tuples(index, index), max_size=n ** 2).map(build_permutation)


@cacheable
def composite(f):
    """Defines a strategy that is built out of potentially arbitrarily many
    other strategies.

    This is intended to be used as a decorator. See the full
    documentation for more details about how to use this function.

    """

    from hypothesis.searchstrategy.morphers import MorpherStrategy
    from hypothesis.internal.reflection import copy_argspec
    argspec = getargspec(f)

    if (
        argspec.defaults is not None and
        len(argspec.defaults) == len(argspec.args)
    ):
        raise InvalidArgument(
            'A default value for initial argument will never be used')
    if len(argspec.args) == 0 and not argspec.varargs:
        raise InvalidArgument(
            'Functions wrapped with composite must take at least one '
            'positional argument.'
        )

    new_argspec = ArgSpec(
        args=argspec.args[1:], varargs=argspec.varargs,
        keywords=argspec.keywords, defaults=argspec.defaults
    )

    base_strategy = streaming(MorpherStrategy())

    @defines_strategy
    @copy_argspec(f.__name__, new_argspec)
    def accept(*args, **kwargs):
        def call_with_draw(morphers):
            index = [0]

            def draw(strategy):
                i = index[0]
                index[0] += 1
                return morphers[i].become(strategy)
            return f(*((draw,) + args), **kwargs)
        return base_strategy.map(call_with_draw)
    return accept


def shared(base, key=None):
    """Returns a strategy that draws a single shared value per run, drawn from
    base. Any two shared instances with the same key will share the same
    value, otherwise the identity of this strategy will be used. That is:

    >>> x = shared(s)
    >>> y = shared(s)

    In the above x and y may draw different (or potentially the same) values.
    In the following they will always draw the same:

    >>> x = shared(s, key="hi")
    >>> y = shared(s, key="hi")
    """
    from hypothesis.searchstrategy.shared import SharedStrategy
    return SharedStrategy(base, key)


@cacheable
def choices():
    """Strategy that generates a function that behaves like random.choice.

    Will note choices made for reproducibility.

    """
    from hypothesis.control import note, current_build_context

    def build_chooser(stream):
        index = [-1]
        choice_count = [0]
        context = current_build_context()
        context.mark_captured()

        def choice(values):
            if not values:
                raise IndexError('Cannot choose from empty sequence')
            k = len(values) - 1
            if k == 0:
                chosen = 0
            else:
                mask = _right_saturate(k)
                while True:
                    index[0] += 1
                    probe = stream[index[0]] & mask
                    if probe <= k:
                        chosen = probe
                        break
            choice_count[0] += 1
            result = values[chosen]
            with context.local():
                note('Choice #%d: %r' % (choice_count[0], result))
            return result
        return choice
    return ReprWrapperStrategy(
        shared(
            builds(build_chooser, streaming(integers(min_value=0))),
            key='hypothesis.strategies.chooser.choice_function'
        ), 'chooser()')


@cacheable
def uuids():
    """Returns a strategy that generates UUIDs.

    All returned values from this will be unique, so e.g. if you do
    lists(uuids()) the resulting list will never contain duplicates.

    """
    from uuid import UUID
    return ReprWrapperStrategy(
        shared(randoms(), key='hypothesis.strategies.uuids.generator').map(
            lambda r: UUID(int=r.getrandbits(128))
        ), 'uuids()')


# Private API below here


def _right_saturate(x):
    x |= (x >> 1)
    x |= (x >> 2)
    x |= (x >> 4)
    x |= (x >> 8)
    x |= (x >> 16)
    x |= (x >> 32)
    return x


def check_type(typ, arg):
    if not isinstance(arg, typ):
        if isinstance(typ, type):
            typ_string = typ.__name__
        else:
            typ_string = 'one of %s' % (
                ', '.join(t.__name__ for t in typ))
        raise InvalidArgument(
            'Expected %s but got %r' % (typ_string, arg,))


def check_strategy(arg):
    check_type(SearchStrategy, arg)


def check_valid_integer(value):
    """Checks that value is either unspecified, or a valid integer.

    Otherwise raises InvalidArgument.

    """
    if value is None:
        return
    check_type(integer_types, value)


def check_valid_bound(value, name):
    """Checks that value is either unspecified, or a valid interval bound.

    Otherwise raises InvalidArgument.

    """
    if value is None:
        return
    if math.isnan(value):
        raise InvalidArgument(u'Invalid end point %s %r' % (value, name))


def check_valid_size(value, name):
    """Checks that value is either unspecified, or a valid non-negative size
    expressed as an integer/float. Otherwise raises InvalidArgument.

    """
    if value is None:
        return
    check_type(integer_types + (float,), value)
    if value < 0:
        raise InvalidArgument(u'Invalid size %s %r < 0' % (value, name))
    if isinstance(value, float) and math.isnan(value):
        raise InvalidArgument(u'Invalid size %s %r' % (value, name))


def check_valid_interval(lower_bound, upper_bound, lower_name, upper_name):
    """Checks that lower_bound and upper_bound are either unspecified, or they
    define a valid interval on the number line.

    Otherwise raises InvalidArgumet.

    """
    if lower_bound is None or upper_bound is None:
        return
    if upper_bound < lower_bound:
        raise InvalidArgument(
            u'Cannot have %s=%r < %s=%r' % (
                upper_name, upper_bound, lower_name, lower_bound
            ))


def check_valid_sizes(min_size, average_size, max_size):
    check_valid_size(min_size, u'min_size')
    check_valid_size(max_size, u'max_size')
    check_valid_size(average_size, u'average_size')
    check_valid_interval(min_size, max_size, u'min_size', u'max_size')
    check_valid_interval(average_size, max_size, u'average_size', u'max_size')
    check_valid_interval(min_size, average_size, u'min_size', u'average_size')

    if average_size is not None:
        if (
            (max_size is None or max_size > 0) and
            average_size is not None and average_size <= 0.0
        ):
            raise InvalidArgument(
                u'Cannot have average_size=%r < min_size=%r' % (
                    average_size, min_size
                ))
