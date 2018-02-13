# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import enum
import math
import datetime as dt
import operator
from decimal import Context, Decimal
from inspect import isclass, isfunction
from fractions import Fraction
from functools import reduce

from hypothesis.errors import InvalidArgument, ResolutionFailed
from hypothesis.control import assume
from hypothesis._settings import note_deprecation
from hypothesis.internal.cache import LRUReusedCache
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.internal.compat import gcd, ceil, floor, hrange, \
    text_type, get_type_hints, getfullargspec, implements_iterator
from hypothesis.internal.floats import is_negative, float_to_int, \
    int_to_float, count_between_floats
from hypothesis.internal.renaming import renamed_arguments
from hypothesis.utils.conventions import infer, not_set
from hypothesis.internal.reflection import proxies, required_args
from hypothesis.internal.validation import check_type, try_convert, \
    check_strategy, check_valid_bound, check_valid_sizes, \
    check_valid_integer, check_valid_interval

__all__ = [
    'nothing',
    'just', 'one_of',
    'none',
    'choices', 'streaming',
    'booleans', 'integers', 'floats', 'complex_numbers', 'fractions',
    'decimals',
    'characters', 'text', 'from_regex', 'binary', 'uuids',
    'tuples', 'lists', 'sets', 'frozensets', 'iterables',
    'dictionaries', 'fixed_dictionaries',
    'sampled_from', 'permutations',
    'datetimes', 'dates', 'times', 'timedeltas',
    'builds',
    'randoms', 'random_module',
    'recursive', 'composite',
    'shared', 'runner', 'data',
    'deferred',
    'from_type', 'register_type_strategy',
]

_strategies = set()


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


STRATEGY_CACHE = LRUReusedCache(1024)


def cacheable(fn):
    @proxies(fn)
    def cached_strategy(*args, **kwargs):
        kwargs_cache_key = set()
        try:
            for k, v in kwargs.items():
                kwargs_cache_key.add((k, convert_value(v)))
        except TypeError:
            return fn(*args, **kwargs)
        cache_key = (
            fn,
            tuple(map(convert_value, args)), frozenset(kwargs_cache_key))
        try:
            return STRATEGY_CACHE[cache_key]
        except TypeError:
            return fn(*args, **kwargs)
        except KeyError:
            result = fn(*args, **kwargs)
            if not isinstance(result, SearchStrategy) or result.is_cacheable:
                STRATEGY_CACHE[cache_key] = result
            return result
    cached_strategy.__clear_cache = STRATEGY_CACHE.clear
    return cached_strategy


def base_defines_strategy(force_reusable):
    """Returns a decorator for strategy functions.

    If force_reusable is True, the generated values are assumed to be
    reusable, i.e. immutable and safe to cache, across multiple test
    invocations.

    """
    def decorator(strategy_definition):
        """A decorator that registers the function as a strategy and makes it
        lazily evaluated."""
        from hypothesis.searchstrategy.lazy import LazyStrategy
        _strategies.add(strategy_definition.__name__)

        @proxies(strategy_definition)
        def accept(*args, **kwargs):
            result = LazyStrategy(strategy_definition, args, kwargs)
            if force_reusable:
                result.force_has_reusable_values = True
                assert result.has_reusable_values
            return result
        return accept
    return decorator


defines_strategy = base_defines_strategy(False)
defines_strategy_with_reusable_values = base_defines_strategy(True)


class Nothing(SearchStrategy):
    def calc_is_empty(self, recur):
        return True

    def do_draw(self, data):
        # This method should never be called because draw() will mark the
        # data as invalid immediately because is_empty is True.
        assert False  # pragma: no cover

    def calc_has_reusable_values(self, recur):
        return True

    def __repr__(self):
        return 'nothing()'

    def map(self, f):
        return self

    def filter(self, f):
        return self

    def flatmap(self, f):
        return self


NOTHING = Nothing()


@cacheable
def nothing():
    """This strategy never successfully draws a value and will always reject on
    an attempt to draw.

    Examples from this strategy do not shrink (because there are none).

    """
    return NOTHING


def just(value):
    """Return a strategy which only generates ``value``.

    Note: ``value`` is not copied. Be wary of using mutable values.

    If ``value`` is the result of a callable, you can use
    :func:`builds(callable) <hypothesis.strategies.builds>` instead
    of ``just(callable())`` to get a fresh value each time.

    Examples from this strategy do not shrink (because there is only one).

    """
    from hypothesis.searchstrategy.misc import JustStrategy

    return JustStrategy(value)


@defines_strategy_with_reusable_values
def none():
    """Return a strategy which only generates None.

    Examples from this strategy do not shrink (because there is only
    one).

    """
    return just(None)


def one_of(*args):
    """Return a strategy which generates values from any of the argument
    strategies.

    This may be called with one iterable argument instead of multiple
    strategy arguments. In which case one_of(x) and one_of(\*x) are
    equivalent.

    Examples from this strategy will generally shrink to ones that come from
    strategies earlier in the list, then shrink according to behaviour of the
    strategy that produced them. In order to get good shrinking behaviour,
    try to put simpler strategies first. e.g. ``one_of(none(), text())`` is
    better than ``one_of(text(), none())``.

    This is especially important when using recursive strategies. e.g.
    ``x = st.deferred(lambda: st.none() | st.tuples(x, x))`` will shrink well,
    but ``x = st.deferred(lambda: st.tuples(x, x) | st.none())`` will shrink
    very badly indeed.

    """
    if len(args) == 1 and not isinstance(args[0], SearchStrategy):
        try:
            args = tuple(args[0])
        except TypeError:
            pass
    from hypothesis.searchstrategy.strategies import OneOfStrategy
    return OneOfStrategy(args)


@cacheable
@defines_strategy_with_reusable_values
def integers(min_value=None, max_value=None):
    """Returns a strategy which generates integers (in Python 2 these may be
    ints or longs).

    If min_value is not None then all values will be >= min_value. If
    max_value is not None then all values will be <= max_value

    Examples from this strategy will shrink towards zero, and negative values
    will also shrink towards positive (i.e. -n may be replaced by +n).

    """

    check_valid_bound(min_value, 'min_value')
    check_valid_bound(max_value, 'max_value')
    check_valid_interval(min_value, max_value, 'min_value', 'max_value')

    from hypothesis.searchstrategy.numbers import IntegersFromStrategy, \
        BoundedIntStrategy, WideRangeIntStrategy

    min_int_value = None if min_value is None else ceil(min_value)
    max_int_value = None if max_value is None else floor(max_value)

    if min_int_value is not None and max_int_value is not None and \
            min_int_value > max_int_value:
        raise InvalidArgument('No integers between min_value=%r and '
                              'max_value=%r' % (min_value, max_value))

    if min_int_value is None:
        if max_int_value is None:
            return (
                WideRangeIntStrategy()
            )
        else:
            return IntegersFromStrategy(0).map(lambda x: max_int_value - x)
    else:
        if max_int_value is None:
            return IntegersFromStrategy(min_int_value)
        else:
            assert min_int_value <= max_int_value
            if min_int_value == max_int_value:
                return just(min_int_value)
            elif min_int_value >= 0:
                return BoundedIntStrategy(min_int_value, max_int_value)
            elif max_int_value <= 0:
                return BoundedIntStrategy(
                    -max_int_value, -min_int_value
                ).map(lambda t: -t)
            else:
                return integers(min_value=0, max_value=max_int_value) | \
                    integers(min_value=min_int_value, max_value=0)


@cacheable
@defines_strategy
def booleans():
    """Returns a strategy which generates instances of bool.

    Examples from this strategy will shrink towards False (i.e.
    shrinking will try to replace True with False where possible).

    """
    from hypothesis.searchstrategy.misc import BoolStrategy
    return BoolStrategy()


@cacheable
@defines_strategy_with_reusable_values
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

    Examples from this strategy have a complicated and hard to explain
    shrinking behaviour, but it tries to improve "human readability". Finite
    numbers will be preferred to infinity and infinity will be preferred to
    NaN.

    """

    if allow_nan is None:
        allow_nan = bool(min_value is None and max_value is None)
    elif allow_nan:
        if min_value is not None or max_value is not None:
            raise InvalidArgument(
                'Cannot have allow_nan=%r, with min_value or max_value' % (
                    allow_nan
                ))

    min_value = try_convert(float, min_value, 'min_value')
    max_value = try_convert(float, max_value, 'max_value')

    check_valid_bound(min_value, 'min_value')
    check_valid_bound(max_value, 'max_value')
    check_valid_interval(min_value, max_value, 'min_value', 'max_value')
    if min_value == float(u'-inf'):
        min_value = None
    if max_value == float(u'inf'):
        max_value = None

    if allow_infinity is None:
        allow_infinity = bool(min_value is None or max_value is None)
    elif allow_infinity:
        if min_value is not None and max_value is not None:
            raise InvalidArgument(
                'Cannot have allow_infinity=%r, with both min_value and '
                'max_value' % (
                    allow_infinity
                ))

    from hypothesis.searchstrategy.numbers import FloatStrategy, \
        FixedBoundedFloatStrategy
    if min_value is None and max_value is None:
        return FloatStrategy(
            allow_infinity=allow_infinity, allow_nan=allow_nan,
        )
    elif min_value is not None and max_value is not None:
        if min_value == max_value:
            return just(min_value)
        elif is_negative(min_value):
            if is_negative(max_value):
                return floats(min_value=-max_value, max_value=-min_value).map(
                    operator.neg
                )
            else:
                return floats(min_value=0.0, max_value=max_value) | floats(
                    min_value=0.0, max_value=-min_value).map(operator.neg)
        elif count_between_floats(min_value, max_value) > 1000:
            return FixedBoundedFloatStrategy(
                lower_bound=min_value, upper_bound=max_value
            )
        else:
            ub_int = float_to_int(max_value)
            lb_int = float_to_int(min_value)
            assert lb_int <= ub_int
            return integers(min_value=lb_int, max_value=ub_int).map(
                int_to_float
            )
    elif min_value is not None:
        if min_value < 0:
            result = floats(
                min_value=0.0
            ) | floats(min_value=min_value, max_value=-0.0)
        else:
            result = (
                floats(allow_infinity=allow_infinity, allow_nan=False).map(
                    lambda x: assume(not math.isnan(x)) and min_value + abs(x)
                )
            )
        if min_value == 0 and not is_negative(min_value):
            result = result.filter(lambda x: math.copysign(1.0, x) == 1)
        return result
    else:
        assert max_value is not None
        if max_value > 0:
            result = floats(
                min_value=0.0,
                max_value=max_value,
            ) | floats(max_value=-0.0)
        else:
            result = (
                floats(allow_infinity=allow_infinity, allow_nan=False).map(
                    lambda x: assume(not math.isnan(x)) and max_value - abs(x)
                )
            )
        if max_value == 0 and is_negative(max_value):
            result = result.filter(is_negative)
        return result


@cacheable
@defines_strategy_with_reusable_values
def complex_numbers():
    """Returns a strategy that generates complex numbers.

    Examples from this strategy shrink by shrinking their component real
    and imaginary parts.

    """
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

    Examples from this strategy shrink by shrinking their component parts.

    """
    for arg in args:
        check_strategy(arg)

    from hypothesis.searchstrategy.collections import TupleStrategy
    return TupleStrategy(args, tuple)


@defines_strategy
def sampled_from(elements):
    """Returns a strategy which generates any value present in ``elements``.

    Note that as with :func:`~hypotheses.strategies.just`, values will not be
    copied and thus you should be careful of using mutable data.

    ``sampled_from`` supports ordered collections, as well as
    :class:`~python:enum.Enum` objects.  :class:`~python:enum.Flag` objects
    may also generate any combination of their members.

    Examples from this strategy shrink by replacing them with values earlier in
    the list. So e.g. sampled_from((10, 1)) will shrink by trying to replace
    1 values with 10, and sampled_from((1, 10)) will shrink by trying to
    replace 10 values with 1.

    """
    from hypothesis.searchstrategy.misc import SampledFromStrategy
    from hypothesis.internal.conjecture.utils import check_sample
    values = check_sample(elements)
    if not values:
        return nothing()
    if len(values) == 1:
        return just(values[0])
    if hasattr(enum, 'Flag') and isclass(elements) and \
            issubclass(elements, enum.Flag):
        # Combinations of enum.Flag members are also members.  We generate
        # these dynamically, because static allocation takes O(2^n) memory.
        return sets(sampled_from(values), min_size=1).map(
            lambda s: reduce(operator.or_, s))
    return SampledFromStrategy(values)


_AVERAGE_LIST_LENGTH = 5.0


@cacheable
@defines_strategy
def lists(
    elements=None, min_size=None, average_size=None, max_size=None,
    unique_by=None, unique=False,
):
    """Returns a list containing values drawn from elements with length in the
    interval [min_size, max_size] (no bounds in that direction if these are
    None). If max_size is 0 then elements may be None and only the empty list
    will be drawn.

    average_size may be used as a size hint to roughly control the size
    of the list but it may not be the actual average of sizes you get, due
    to a variety of factors.

    If unique is True (or something that evaluates to True), we compare direct
    object equality, as if unique_by was `lambda x: x`. This comparison only
    works for hashable types.

    if unique_by is not None it must be a function returning a hashable type
    when given a value drawn from elements. The resulting list will satisfy the
    condition that for i != j, unique_by(result[i]) != unique_by(result[j]).

    Examples from this strategy shrink by trying to remove elements from the
    list, and by shrinking each individual element of the list.

    """
    check_valid_sizes(min_size, average_size, max_size)
    if elements is None or (max_size is not None and max_size <= 0):
        if max_size is None or max_size > 0:
            raise InvalidArgument(
                u'Cannot create non-empty lists without an element type'
            )
        else:
            return builds(list)
    check_strategy(elements)
    if unique:
        if unique_by is not None:
            raise InvalidArgument((
                'cannot specify both unique and unique_by (you probably only '
                'want to set unique_by)'
            ))
        else:
            def unique_by(x):
                return x

    if min_size is None:
        min_size = 0

    if max_size is None:
        max_size = float('inf')

    if average_size is None:
        average_size = max(
            _AVERAGE_LIST_LENGTH,
            min_size * 2
        )
        if max_size < float('inf'):
            average_size = min(average_size, 0.5 * (min_size + max_size))

    from hypothesis.searchstrategy.collections import ListStrategy, \
        UniqueListStrategy
    if unique_by is not None:
        return UniqueListStrategy(
            elements=elements,
            average_size=average_size,
            max_size=max_size,
            min_size=min_size,
            key=unique_by
        )
    else:
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

    Examples from this strategy shrink by trying to remove elements from the
    set, and by shrinking each individual element of the set.

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
def iterables(elements=None, min_size=None, average_size=None, max_size=None,
              unique_by=None, unique=False):
    """This has the same behaviour as lists, but returns iterables instead.

    Some iterables cannot be indexed (e.g. sets) and some do not have a
    fixed length (e.g. generators). This strategy produces iterators,
    which cannot be indexed and do not have a fixed length. This ensures
    that you do not accidentally depend on sequence behaviour.

    """
    @implements_iterator
    class PrettyIter(object):
        def __init__(self, values):
            self._values = values
            self._iter = iter(self._values)

        def __iter__(self):
            return self._iter

        def __next__(self):
            return next(self._iter)

        def __repr__(self):
            return 'iter({!r})'.format(self._values)

    return lists(
        elements=elements, min_size=min_size, average_size=average_size,
        max_size=max_size, unique_by=unique_by, unique=unique
    ).map(PrettyIter)


@defines_strategy
def fixed_dictionaries(mapping):
    """Generates a dictionary of the same type as mapping with a fixed set of
    keys mapping to strategies. mapping must be a dict subclass.

    Generated values have all keys present in mapping, with the
    corresponding values drawn from mapping[key]. If mapping is an
    instance of OrderedDict the keys will also be in the same order,
    otherwise the order is arbitrary.

    Examples from this strategy shrink by shrinking each individual value in
    the generated dictionary.

    """
    from hypothesis.searchstrategy.collections import FixedKeysDictStrategy
    check_type(dict, mapping, 'mapping')
    for v in mapping.values():
        check_strategy(v)
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

    Examples from this strategy shrink by trying to remove keys from the
    generated dictionary, and by shrinking each generated key and value.

    """
    check_valid_sizes(min_size, average_size, max_size)
    if max_size == 0:
        return fixed_dictionaries(dict_class())
    check_strategy(keys)
    check_strategy(values)

    return lists(
        tuples(keys, values),
        min_size=min_size, average_size=average_size, max_size=max_size,
        unique_by=lambda x: x[0]
    ).map(dict_class)


@defines_strategy
def streaming(elements):
    """Generates an infinite stream of values where each value is drawn from
    elements.

    The result is iterable (the iterator will never terminate) and
    indexable.

    Examples from this strategy shrink by trying to shrink each value drawn.

    .. deprecated:: 3.15.0
        Use :func:`data() <hypothesis.strategies.data>` instead.

    """
    note_deprecation(
        'streaming() has been deprecated. Use the data() strategy instead and '
        'replace stream iteration with data.draw() calls.'
    )

    check_strategy(elements)

    from hypothesis.searchstrategy.streams import StreamStrategy
    return StreamStrategy(elements)


@cacheable
@defines_strategy_with_reusable_values
def characters(whitelist_categories=None, blacklist_categories=None,
               blacklist_characters=None, min_codepoint=None,
               max_codepoint=None, whitelist_characters=None):
    """Generates unicode text type (unicode on python 2, str on python 3)
    characters following specified filtering rules.

    When no filtering rules are specifed, any character can be produced.

    If ``min_codepoint`` or ``max_codepoint`` is specifed, then only
    characters having a codepoint in that range will be produced.

    If ``whitelist_categories`` is specified, then only characters from those
    Unicode categories will be produced. This is a further restriction,
    characters must also satisfy ``min_codepoint`` and ``max_codepoint``.

    If ``blacklist_categories`` is specified, then any character from those
    categories will not be produced. This is a further restriction,
    characters that match both ``whitelist_categories`` and
    ``blacklist_categories`` will not be produced.

    If ``whitelist_characters`` is specified, then any additional characters
    in that list will also be produced.

    If ``blacklist_characters`` is specified, then any characters in that list
    will be not be produced. Any overlap between ``whitelist_characters`` and
    ``blacklist_characters`` will raise an exception.

    Examples from this strategy shrink towards smaller codepoints.

    """
    if (
        min_codepoint is not None and max_codepoint is not None and
        min_codepoint > max_codepoint
    ):
        raise InvalidArgument(
            'Cannot have min_codepoint=%d > max_codepoint=%d ' % (
                min_codepoint, max_codepoint
            )
        )
    if all((whitelist_characters is not None,
            min_codepoint is None,
            max_codepoint is None,
            whitelist_categories is None,
            blacklist_categories is None,
            )):
        raise InvalidArgument(
            'Cannot have just whitelist_characters=%r alone, '
            'it would have no effect. Perhaps you want sampled_from()' % (
                whitelist_characters,
            )
        )
    if (
        whitelist_characters is not None and
        blacklist_characters is not None and
        set(blacklist_characters).intersection(set(whitelist_characters))
    ):
        raise InvalidArgument(
            'Characters %r are present in both whitelist_characters=%r, and '
            'blacklist_characters=%r' % (
                set(blacklist_characters).intersection(
                    set(whitelist_characters)
                ),
                whitelist_characters, blacklist_characters,
            )
        )

    from hypothesis.searchstrategy.strings import OneCharStringStrategy
    return OneCharStringStrategy(whitelist_categories=whitelist_categories,
                                 blacklist_categories=blacklist_categories,
                                 blacklist_characters=blacklist_characters,
                                 min_codepoint=min_codepoint,
                                 max_codepoint=max_codepoint,
                                 whitelist_characters=whitelist_characters)


@cacheable
@defines_strategy_with_reusable_values
def text(
    alphabet=None,
    min_size=None, average_size=None, max_size=None
):
    """Generates values of a unicode text type (unicode on python 2, str on
    python 3) with values drawn from alphabet, which should be an iterable of
    length one strings or a strategy generating such. If it is None it will
    default to generating the full unicode range (excluding surrogate
    characters). If it is an empty collection this will only generate empty
    strings.

    min_size, max_size and average_size have the usual interpretations.

    Examples from this strategy shrink towards shorter strings, and with the
    characters in the text shrinking as per the alphabet strategy.

    """
    from hypothesis.searchstrategy.strings import StringStrategy
    if alphabet is None:
        char_strategy = characters(blacklist_categories=('Cs',))
    elif not alphabet:
        if (min_size or 0) > 0:
            raise InvalidArgument(
                'Invalid min_size %r > 0 for empty alphabet' % (
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
def from_regex(regex):
    """Generates strings that contain a match for the given regex (i.e. ones
    for which :func:`re.search` will return a non-None result).

    ``regex`` may be a pattern or :func:`compiled regex <python:re.compile>`.
    Both byte-strings and unicode strings are supported, and will generate
    examples of the same type.

    You can use regex flags such as :const:`re.IGNORECASE`, :const:`re.DOTALL`
    or :const:`re.UNICODE` to control generation. Flags can be passed either
    in compiled regex or inside the pattern with a ``(?iLmsux)`` group.

    Some regular expressions are only partly supported - the underlying
    strategy checks local matching and relies on filtering to resolve
    context-dependent expressions.  Using too many of these constructs may
    cause health-check errors as too many examples are filtered out. This
    mainly includes (positive or negative) lookahead and lookbehind groups.

    If you want the generated string to match the whole regex you should use
    boundary markers. So e.g. ``r"\\A.\\Z"`` will return a single character
    string, while ``"."`` will return any string, and ``r"\\A.$"`` will return
    a single character optionally followed by a ``"\\n"``.

    Examples from this strategy shrink towards shorter strings and lower
    character values.

    """
    from hypothesis.searchstrategy.regex import regex_strategy
    return regex_strategy(regex)


@cacheable
@defines_strategy_with_reusable_values
def binary(
    min_size=None, average_size=None, max_size=None
):
    """Generates the appropriate binary type (str in python 2, bytes in python
    3).

    min_size, average_size and max_size have the usual interpretations.

    Examples from this strategy shrink towards smaller strings and lower byte
    values.

    """
    from hypothesis.searchstrategy.strings import BinaryStringStrategy, \
        FixedSizeBytes
    check_valid_sizes(min_size, average_size, max_size)
    if min_size == max_size is not None:
        return FixedSizeBytes(min_size)
    return BinaryStringStrategy(
        lists(
            integers(min_value=0, max_value=255),
            average_size=average_size, min_size=min_size, max_size=max_size
        )
    )


@cacheable
@defines_strategy
def randoms():
    """Generates instances of Random (actually a Hypothesis specific
    RandomWithSeed class which displays what it was initially seeded with)

    Examples from this strategy shrink to seeds closer to zero.

    """
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

    Examples from these strategy shrink to seeds closer to zero.

    """
    from hypothesis.control import cleanup
    import random

    class RandomModule(SearchStrategy):
        def do_draw(self, data):
            data.can_reproduce_example_from_repr = False
            seed = data.draw(integers())
            state = random.getstate()
            random.seed(seed)
            cleanup(lambda: random.setstate(state))
            return RandomSeeder(seed)

    return shared(RandomModule(), 'hypothesis.strategies.random_module()')


@cacheable
@defines_strategy
def builds(*callable_and_args, **kwargs):
    """Generates values by drawing from ``args`` and ``kwargs`` and passing
    them to the callable (provided as the first positional argument) in the
    appropriate argument position.

    e.g. ``builds(target, integers(), flag=booleans())`` would draw an
    integer ``i`` and a boolean ``b`` and call ``target(i, flag=b)``.

    If the callable has type annotations, they will be used to infer a strategy
    for required arguments that were not passed to builds.  You can also tell
    builds to infer a strategy for an optional argument by passing the special
    value :const:`hypothesis.infer` as a keyword argument to
    builds, instead of a strategy for that argument to the callable.

    Examples from this strategy shrink by shrinking the argument values to
    the callable.

    """
    if callable_and_args:
        target, args = callable_and_args[0], callable_and_args[1:]
        if not callable(target):
            raise InvalidArgument(
                'The first positional argument to builds() must be a callable '
                'target to construct.')
    elif 'target' in kwargs and callable(kwargs['target']):
        args = []
        note_deprecation(
            'Specifying the target as a keyword argument to builds() is '
            'deprecated. Provide it as the first positional argument instead.')
        target = kwargs.pop('target')
    else:
        raise InvalidArgument(
            'builds() must be passed a callable as the first positional '
            'argument, but no positional arguments were given.')

    if infer in args:
        # Avoid an implementation nightmare juggling tuples and worse things
        raise InvalidArgument('infer was passed as a positional argument to '
                              'builds(), but is only allowed as a keyword arg')
    hints = get_type_hints(target.__init__ if isclass(target) else target)
    for kw in [k for k, v in kwargs.items() if v is infer]:
        if kw not in hints:
            raise InvalidArgument(
                'passed %s=infer for %s, but %s has no type annotation'
                % (kw, target.__name__, kw))
        kwargs[kw] = from_type(hints[kw])
    required = required_args(target, args, kwargs)
    for ms in set(hints) & (required or set()):
        kwargs[ms] = from_type(hints[ms])
    return tuples(tuples(*args), fixed_dictionaries(kwargs)).map(
        lambda value: target(*value[0], **value[1])
    )


def _defer_from_type(func):
    """Decorator to make from_type lazy to support recursive definitions."""
    @proxies(func)
    def inner(*args, **kwargs):
        return deferred(lambda: func(*args, **kwargs))
    return inner


@cacheable
@_defer_from_type
def from_type(thing):
    """Looks up the appropriate search strategy for the given type.

    ``from_type`` is used internally to fill in missing arguments to
    :func:`~hypothesis.strategies.builds` and can be used interactively
    to explore what strategies are available or to debug type resolution.

    You can use :func:`~hypothesis.strategies.register_type_strategy` to
    handle your custom types, or to globally redefine certain strategies -
    for example excluding NaN from floats, or use timezone-aware instead of
    naive time and datetime strategies.

    The resolution logic may be changed in a future version, but currently
    tries these four options:

    1. If ``thing`` is in the default lookup mapping or user-registered lookup,
       return the corresponding strategy.  The default lookup covers all types
       with Hypothesis strategies, including extras where possible.
    2. If ``thing`` is from the :mod:`python:typing` module, return the
       corresponding strategy (special logic).
    3. If ``thing`` has one or more subtypes in the merged lookup, return
       the union of the strategies for those types that are not subtypes of
       other elements in the lookup.
    4. Finally, if ``thing`` has type annotations for all required arguments,
       it is resolved via :func:`~hypothesis.strategies.builds`.

    """
    from hypothesis.searchstrategy import types
    try:
        import typing
        if not isinstance(thing, type):
            # At runtime, `typing.NewType` returns an identity function rather
            # than an actual type, but we can check that for a possible match
            # and then read the magic attribute to unwrap it.
            if all([
                hasattr(thing, '__supertype__'), hasattr(typing, 'NewType'),
                isfunction(thing), getattr(thing, '__module__', 0) == 'typing'
            ]):
                return from_type(thing.__supertype__)
            # Under Python 3.6, Unions are not instances of `type` - but we
            # still want to resolve them!
            if getattr(thing, '__origin__', None) is typing.Union:
                args = sorted(thing.__args__, key=types.type_sorting_key)
                return one_of([from_type(t) for t in args])
        # We can't resolve forward references, and under Python 3.5 (only)
        # a forward reference is an instance of type.  Hence, explicit check:
        elif type(thing) == typing._ForwardRef:  # pragma: no cover
            raise ResolutionFailed(
                'thing=%s cannot be resolved.  Upgrading to python>=3.6 may '
                'fix this problem via improvements to the typing module.'
                % (thing,))
    except ImportError:  # pragma: no cover
        pass
    if not isinstance(thing, type):
        raise InvalidArgument('thing=%s must be a type' % (thing,))
    # Now that we know `thing` is a type, the first step is to check for an
    # explicitly registered strategy.  This is the best (and hopefully most
    # common) way to resolve a type to a strategy.  Note that the value in the
    # lookup may be a strategy or a function from type -> strategy; and we
    # convert empty results into an explicit error.
    if thing in types._global_type_lookup:
        strategy = types._global_type_lookup[thing]
        if not isinstance(strategy, SearchStrategy):
            strategy = strategy(thing)
        if strategy.is_empty:
            raise ResolutionFailed(
                'Error: %r resolved to an empty strategy' % (thing,))
        return strategy
    # If there's no explicitly registered strategy, maybe a subtype of thing
    # is registered - if so, we can resolve it to the subclass strategy.
    # We'll start by checking if thing is from from the typing module,
    # because there are several special cases that don't play well with
    # subclass and instance checks.
    try:
        import typing
        if isinstance(thing, typing.TypingMeta):
            return types.from_typing_type(thing)
    except ImportError:  # pragma: no cover
        pass
    # If it's not from the typing module, we get all registered types that are
    # a subclass of `thing` and are not themselves a subtype of any other such
    # type.  For example, `Number -> integers() | floats()`, but bools() is
    # not included because bool is a subclass of int as well as Number.
    strategies = [
        v if isinstance(v, SearchStrategy) else v(thing)
        for k, v in types._global_type_lookup.items()
        if issubclass(k, thing) and
        sum(types.try_issubclass(k, T) for T in types._global_type_lookup) == 1
    ]
    empty = ', '.join(repr(s) for s in strategies if s.is_empty)
    if empty:
        raise ResolutionFailed(
            'Could not resolve %s to a strategy; consider using '
            'register_type_strategy' % empty)
    elif strategies:
        return one_of(strategies)
    # If we don't have a strategy registered for this type or any subtype, we
    # may be able to fall back on type annotations.
    # Types created via typing.NamedTuple use a custom attribute instead -
    # but we can still use builds(), if we work out the right kwargs.
    if issubclass(thing, tuple) and hasattr(thing, '_fields') \
            and hasattr(thing, '_field_types'):
        kwargs = {k: from_type(thing._field_types[k]) for k in thing._fields}
        return builds(thing, **kwargs)
    if issubclass(thing, enum.Enum):
        assert len(thing), repr(thing) + ' has no members to sample'
        return sampled_from(thing)
    # If the constructor has an annotation for every required argument,
    # we can (and do) use builds() without supplying additional arguments.
    required = required_args(thing)
    if not required or required.issubset(get_type_hints(thing.__init__)):
        return builds(thing)
    # We have utterly failed, and might as well say so now.
    raise ResolutionFailed('Could not resolve %r to a strategy; consider '
                           'using register_type_strategy' % (thing,))


@cacheable
@defines_strategy_with_reusable_values
def fractions(min_value=None, max_value=None, max_denominator=None):
    """Returns a strategy which generates Fractions.

    If min_value is not None then all generated values are no less than
    min_value.  If max_value is not None then all generated values are no
    greater than max_value.  min_value and max_value may be anything accepted
    by the :class:`~fractions.Fraction` constructor.

    If max_denominator is not None then the denominator of any generated
    values is no greater than max_denominator. Note that max_denominator must
    be None or a positive integer.

    Examples from this strategy shrink towards smaller denominators, then
    closer to zero.

    """
    min_value = try_convert(Fraction, min_value, 'min_value')
    max_value = try_convert(Fraction, max_value, 'max_value')

    check_valid_interval(min_value, max_value, 'min_value', 'max_value')
    check_valid_integer(max_denominator)

    if max_denominator is not None:
        if max_denominator < 1:
            raise InvalidArgument(
                'max_denominator=%r must be >= 1' % max_denominator)

        def fraction_bounds(value):
            """Find the best lower and upper approximation for value."""
            # Adapted from CPython's Fraction.limit_denominator here:
            # https://github.com/python/cpython/blob/3.6/Lib/fractions.py#L219
            if value is None or value.denominator <= max_denominator:
                return value, value
            p0, q0, p1, q1 = 0, 1, 1, 0
            n, d = value.numerator, value.denominator
            while True:
                a = n // d
                q2 = q0 + a * q1
                if q2 > max_denominator:
                    break
                p0, q0, p1, q1 = p1, q1, p0 + a * p1, q2
                n, d = d, n - a * d
            k = (max_denominator - q0) // q1
            low, high = Fraction(p1, q1), Fraction(p0 + k * p1, q0 + k * q1)
            assert low < value < high
            return low, high

        # Take the high approximation for min_value and low for max_value
        bounds = (max_denominator, min_value, max_value)
        _, min_value = fraction_bounds(min_value)
        max_value, _ = fraction_bounds(max_value)

        if None not in (min_value, max_value) and min_value > max_value:
            raise InvalidArgument(
                'There are no fractions with a denominator <= %r between '
                'min_value=%r and max_value=%r' % bounds)

    if min_value is not None and min_value == max_value:
        return just(min_value)

    def dm_func(denom):
        """Take denom, construct numerator strategy, and build fraction."""
        # Four cases of algebra to get integer bounds and scale factor.
        min_num, max_num = None, None
        if max_value is None and min_value is None:
            pass
        elif min_value is None:
            max_num = denom * max_value.numerator
            denom *= max_value.denominator
        elif max_value is None:
            min_num = denom * min_value.numerator
            denom *= min_value.denominator
        else:
            low = min_value.numerator * max_value.denominator
            high = max_value.numerator * min_value.denominator
            scale = min_value.denominator * max_value.denominator
            # After calculating our integer bounds and scale factor, we remove
            # the gcd to avoid drawing more bytes for the example than needed.
            # Note that `div` can be at most equal to `scale`.
            div = gcd(scale, gcd(low, high))
            min_num = denom * low // div
            max_num = denom * high // div
            denom *= scale // div

        return builds(
            Fraction,
            integers(min_value=min_num, max_value=max_num),
            just(denom)
        )

    if max_denominator is None:
        return integers(min_value=1).flatmap(dm_func)

    return integers(1, max_denominator).flatmap(dm_func).map(
        lambda f: f.limit_denominator(max_denominator))


@cacheable
@defines_strategy_with_reusable_values
def decimals(min_value=None, max_value=None,
             allow_nan=None, allow_infinity=None, places=None):
    """Generates instances of :class:`decimals.Decimal`, which may be:

    - A finite rational number, between ``min_value`` and ``max_value``.
    - Not a Number, if ``allow_nan`` is True.  None means "allow NaN, unless
      ``min_value`` and ``max_value`` are not None".
    - Positive or negative infinity, if ``max_value`` and ``min_value``
      respectively are None, and ``allow_infinity`` is not False.  None means
      "allow infinity, unless excluded by the min and max values".

    Note that where floats have one ``NaN`` value, Decimals have four: signed,
    and either *quiet* or *signalling*.  See `the decimal module docs
    <https://docs.python.org/3/library/decimal.html#special-values>`_ for
    more information on special values.

    If ``places`` is not None, all finite values drawn from the strategy will
    have that number of digits after the decimal place.

    Examples from this strategy do not have a well defined shrink order but
    try to maximize human readability when shrinking.

    """
    # Convert min_value and max_value to Decimal values, and validate args
    check_valid_integer(places)
    if places is not None and places < 0:
        raise InvalidArgument('places=%r may not be negative' % places)

    if min_value is not None:
        min_value = try_convert(Decimal, min_value, 'min_value')
        if min_value.is_infinite() and min_value < 0:
            if not (allow_infinity or allow_infinity is None):
                raise InvalidArgument('allow_infinity=%r, but min_value=%r'
                                      % (allow_infinity, min_value))
            min_value = None
        elif not min_value.is_finite():
            # This could be positive infinity, quiet NaN, or signalling NaN
            raise InvalidArgument(u'Invalid min_value=%r' % min_value)
    if max_value is not None:
        max_value = try_convert(Decimal, max_value, 'max_value')
        if max_value.is_infinite() and max_value > 0:
            if not (allow_infinity or allow_infinity is None):
                raise InvalidArgument('allow_infinity=%r, but max_value=%r'
                                      % (allow_infinity, max_value))
            max_value = None
        elif not max_value.is_finite():
            raise InvalidArgument(u'Invalid max_value=%r' % max_value)
    check_valid_interval(min_value, max_value, 'min_value', 'max_value')

    if allow_infinity and (None not in (min_value, max_value)):
        raise InvalidArgument('Cannot allow infinity between finite bounds')
    # Set up a strategy for finite decimals.  Note that both floating and
    # fixed-point decimals require careful handling to remain isolated from
    # any external precision context - in short, we always work out the
    # required precision for lossless operation and use context methods.
    if places is not None:
        # Fixed-point decimals are basically integers with a scale factor
        def ctx(val):
            """Return a context in which this value is lossless."""
            precision = ceil(math.log10(abs(val) or 1)) + places + 1
            return Context(prec=max([precision, 1]))

        def int_to_decimal(val):
            context = ctx(val)
            return context.quantize(context.multiply(val, factor), factor)

        factor = Decimal(10) ** -places
        min_num, max_num = None, None
        if min_value is not None:
            min_num = ceil(ctx(min_value).divide(min_value, factor))
        if max_value is not None:
            max_num = floor(ctx(max_value).divide(max_value, factor))
        if None not in (min_num, max_num) and min_num > max_num:
            raise InvalidArgument(
                'There are no decimals with %d places between min_value=%r '
                'and max_value=%r ' % (places, min_value, max_value))
        strat = integers(min_num, max_num).map(int_to_decimal)
    else:
        # Otherwise, they're like fractions featuring a power of ten
        def fraction_to_decimal(val):
            precision = ceil(math.log10(abs(val.numerator) or 1) +
                             math.log10(val.denominator)) + 1
            return Context(prec=precision or 1).divide(
                Decimal(val.numerator), val.denominator)

        strat = fractions(min_value, max_value).map(fraction_to_decimal)
    # Compose with sampled_from for infinities and NaNs as appropriate
    special = []
    if allow_nan or (allow_nan is None and (None in (min_value, max_value))):
        special.extend(map(Decimal, ('NaN', '-NaN', 'sNaN', '-sNaN')))
    if allow_infinity or (allow_infinity is max_value is None):
        special.append(Decimal('Infinity'))
    if allow_infinity or (allow_infinity is min_value is None):
        special.append(Decimal('-Infinity'))
    return strat | sampled_from(special)


def recursive(base, extend, max_leaves=100):
    """base: A strategy to start from.

    extend: A function which takes a strategy and returns a new strategy.

    max_leaves: The maximum number of elements to be drawn from base on a given
    run.

    This returns a strategy ``S`` such that ``S = extend(base | S)``. That is,
    values may be drawn from base, or from any strategy reachable by mixing
    applications of | and extend.

    An example may clarify: ``recursive(booleans(), lists)`` would return a
    strategy that may return arbitrarily nested and mixed lists of booleans.
    So e.g. ``False``, ``[True]``, ``[False, []]``, and ``[[[[True]]]]`` are
    all valid values to be drawn from that strategy.

    Examples from this strategy shrink by trying to reduce the amount of
    recursion and by shrinking according to the shrinking behaviour of base
    and the result of extend.

    """

    from hypothesis.searchstrategy.recursive import RecursiveStrategy
    return RecursiveStrategy(base, extend, max_leaves)


@defines_strategy
def permutations(values):
    """Return a strategy which returns permutations of the collection
    ``values``.

    Examples from this strategy shrink by trying to become closer to the
    original order of values.

    """
    from hypothesis.internal.conjecture.utils import integer_range

    values = list(values)
    if not values:
        return builds(list)

    class PermutationStrategy(SearchStrategy):

        def do_draw(self, data):
            # Reversed Fisher-Yates shuffle. Reverse order so that it shrinks
            # propertly: This way we prefer things that are lexicographically
            # closer to the identity.
            result = list(values)
            for i in hrange(len(result)):
                j = integer_range(data, i, len(result) - 1)
                result[i], result[j] = result[j], result[i]
            return result
    return PermutationStrategy()


@defines_strategy_with_reusable_values
@renamed_arguments(
    min_datetime='min_value',
    max_datetime='max_value',
)
def datetimes(
    min_value=dt.datetime.min, max_value=dt.datetime.max,
    timezones=none(),
    min_datetime=None, max_datetime=None,
):
    """A strategy for generating datetimes, which may be timezone-aware.

    This strategy works by drawing a naive datetime between ``min_datetime``
    and ``max_datetime``, which must both be naive (have no timezone).

    ``timezones`` must be a strategy that generates tzinfo objects (or None,
    which is valid for naive datetimes).  A value drawn from this strategy
    will be added to a naive datetime, and the resulting tz-aware datetime
    returned.

    .. note::
        tz-aware datetimes from this strategy may be ambiguous or non-existent
        due to daylight savings, leap seconds, timezone and calendar
        adjustments, etc.  This is intentional, as malformed timestamps are a
        common source of bugs.

    :py:func:`hypothesis.extra.timezones` requires the ``pytz`` package, but
    provides all timezones in the Olsen database.  If you also want to allow
    naive datetimes, combine strategies like ``none() | timezones()``.

    Alternatively, you can create a list of the timezones you wish to allow
    (e.g. from the standard library, ``datetutil``, or ``pytz``) and use
    :py:func:`sampled_from`.  Ensure that simple values such as None or UTC
    are at the beginning of the list for proper minimisation.

    Examples from this strategy shrink towards midnight on January 1st 2000.

    """
    # Why must bounds be naive?  In principle, we could also write a strategy
    # that took aware bounds, but the API and validation is much harder.
    # If you want to generate datetimes between two particular momements in
    # time I suggest (a) just filtering out-of-bounds values; (b) if bounds
    # are very close, draw a value and subtract it's UTC offset, handling
    # overflows and nonexistent times; or (c) do something customised to
    # handle datetimes in e.g. a four-microsecond span which is not
    # representable in UTC.  Handling (d), all of the above, leads to a much
    # more complex API for all users and a useful feature for very few.
    from hypothesis.searchstrategy.datetime import DatetimeStrategy

    check_type(dt.datetime, min_value, 'min_value')
    check_type(dt.datetime, max_value, 'max_value')
    if min_value.tzinfo is not None:
        raise InvalidArgument('min_value=%r must not have tzinfo'
                              % (min_value,))
    if max_value.tzinfo is not None:
        raise InvalidArgument('max_value=%r must not have tzinfo'
                              % (max_value,))
    check_valid_interval(min_value, max_value,
                         'min_value', 'max_value')
    if not isinstance(timezones, SearchStrategy):
        raise InvalidArgument(
            'timezones=%r must be a SearchStrategy that can provide tzinfo '
            'for datetimes (either None or dt.tzinfo objects)' % (timezones,))
    return DatetimeStrategy(min_value, max_value, timezones)


@defines_strategy_with_reusable_values
@renamed_arguments(
    min_date='min_value',
    max_date='max_value',
)
def dates(
    min_value=dt.date.min, max_value=dt.date.max,
    min_date=None, max_date=None,
):
    """A strategy for dates between ``min_date`` and ``max_date``.

    Examples from this strategy shrink towards January 1st 2000.

    """
    from hypothesis.searchstrategy.datetime import DateStrategy

    check_type(dt.date, min_value, 'min_value')
    check_type(dt.date, max_value, 'max_value')
    check_valid_interval(min_value, max_value, 'min_value', 'max_value')
    if min_value == max_value:
        return just(min_value)
    return DateStrategy(min_value, max_value)


@defines_strategy_with_reusable_values
@renamed_arguments(
    min_time='min_value',
    max_time='max_value',
)
def times(
    min_value=dt.time.min, max_value=dt.time.max, timezones=none(),
    min_time=None, max_time=None,
):
    """A strategy for times between ``min_time`` and ``max_time``.

    The ``timezones`` argument is handled as for :py:func:`datetimes`.

    Examples from this strategy shrink towards midnight, with the timezone
    component shrinking as for the strategy that provided it.

    """
    check_type(dt.time, min_value, 'min_value')
    check_type(dt.time, max_value, 'max_value')
    if min_value.tzinfo is not None:
        raise InvalidArgument('min_value=%r must not have tzinfo' % min_value)
    if max_value.tzinfo is not None:
        raise InvalidArgument('max_value=%r must not have tzinfo' % max_value)
    check_valid_interval(min_value, max_value, 'min_value', 'max_value')
    day = dt.date(2000, 1, 1)
    return datetimes(min_value=dt.datetime.combine(day, min_value),
                     max_value=dt.datetime.combine(day, max_value),
                     timezones=timezones).map(lambda t: t.timetz())


@defines_strategy_with_reusable_values
@renamed_arguments(
    min_delta='min_value',
    max_delta='max_value',
)
def timedeltas(
    min_value=dt.timedelta.min, max_value=dt.timedelta.max,
    min_delta=None, max_delta=None
):
    """A strategy for timedeltas between ``min_value`` and ``max_value``.

    Examples from this strategy shrink towards zero.

    """
    from hypothesis.searchstrategy.datetime import TimedeltaStrategy

    check_type(dt.timedelta, min_value, 'min_value')
    check_type(dt.timedelta, max_value, 'max_value')
    check_valid_interval(min_value, max_value, 'min_value', 'max_value')
    if min_value == max_value:
        return just(min_value)
    return TimedeltaStrategy(min_value=min_value, max_value=max_value)


@cacheable
def composite(f):
    """Defines a strategy that is built out of potentially arbitrarily many
    other strategies.

    This is intended to be used as a decorator. See
    :ref:`the full documentation for more details <composite-strategies>`
    about how to use this function.

    Examples from this strategy shrink by shrinking the output of each draw
    call.

    """

    from hypothesis.internal.reflection import define_function_signature
    from hypothesis.searchstrategy.strategies import calc_label
    argspec = getfullargspec(f)

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

    annots = {k: v for k, v in argspec.annotations.items()
              if k in (argspec.args + argspec.kwonlyargs + ['return'])}
    new_argspec = argspec._replace(args=argspec.args[1:], annotations=annots)

    label = calc_label(f)

    @defines_strategy
    @define_function_signature(f.__name__, f.__doc__, new_argspec)
    def accept(*args, **kwargs):
        class CompositeStrategy(SearchStrategy):

            def do_draw(self, data):
                first_draw = [True]

                def draw(strategy):
                    first_draw[0] = False
                    return data.draw(strategy)

                return f(draw, *args, **kwargs)

            @property
            def label(self):
                return label
        return CompositeStrategy()
    accept.__module__ = f.__module__
    return accept


def shared(base, key=None):
    """Returns a strategy that draws a single shared value per run, drawn from
    base. Any two shared instances with the same key will share the same value,
    otherwise the identity of this strategy will be used. That is:

    >>> s = integers()  # or any other strategy
    >>> x = shared(s)
    >>> y = shared(s)

    In the above x and y may draw different (or potentially the same) values.
    In the following they will always draw the same:

    >>> x = shared(s, key="hi")
    >>> y = shared(s, key="hi")

    Examples from this strategy shrink as per their base strategy.

    """
    from hypothesis.searchstrategy.shared import SharedStrategy
    return SharedStrategy(base, key)


@defines_strategy
def choices():
    """Strategy that generates a function that behaves like random.choice.

    Will note choices made for reproducibility.

    .. deprecated:: 3.15.0

        Use :func:`data() <hypothesis.strategies.data>` with
        :func:`sampled_from() <hypothesis.strategies.sampled_from>` instead.

    Examples from this strategy shrink by making each choice function return
    an earlier value in the sequence passed to it.

    """
    from hypothesis.control import note, current_build_context
    from hypothesis.internal.conjecture.utils import choice, check_sample

    note_deprecation(
        'choices() has been deprecated. Use the data() strategy instead and '
        'replace its usage with data.draw(sampled_from(elements))) calls.'
    )

    class Chooser(object):

        def __init__(self, build_context, data):
            self.build_context = build_context
            self.data = data
            self.choice_count = 0

        def __call__(self, values):
            if not values:
                raise IndexError('Cannot choose from empty sequence')
            result = choice(self.data, check_sample(values))
            with self.build_context.local():
                self.choice_count += 1
                note('Choice #%d: %r' % (self.choice_count, result))
            return result

        def __repr__(self):
            return 'choice'

    class ChoiceStrategy(SearchStrategy):
        supports_find = False

        def do_draw(self, data):
            data.can_reproduce_example_from_repr = False
            return Chooser(current_build_context(), data)

    return shared(
        ChoiceStrategy(),
        key='hypothesis.strategies.chooser.choice_function'
    )


@cacheable
@defines_strategy_with_reusable_values
def uuids(version=None):
    """Returns a strategy that generates :class:`UUIDs <uuid.UUID>`.

    If the optional version argument is given, value is passed through
    to :class:`~python:uuid.UUID` and only UUIDs of that version will
    be generated.

    All returned values from this will be unique, so e.g. if you do
    ``lists(uuids())`` the resulting list will never contain duplicates.

    Examples from this strategy don't have any meaningful shrink order.

    """
    from uuid import UUID
    if version not in (None, 1, 2, 3, 4, 5):
        raise InvalidArgument((
            'version=%r, but version must be in (None, 1, 2, 3, 4, 5) '
            'to pass to the uuid.UUID constructor.') % (version, )
        )
    return shared(randoms(), key='hypothesis.strategies.uuids.generator').map(
        lambda r: UUID(version=version, int=r.getrandbits(128))
    )


@defines_strategy_with_reusable_values
def runner(default=not_set):
    """A strategy for getting "the current test runner", whatever that may be.
    The exact meaning depends on the entry point, but it will usually be the
    associated 'self' value for it.

    If there is no current test runner and a default is provided, return
    that default. If no default is provided, raises InvalidArgument.

    Examples from this strategy do not shrink (because there is only one).

    """
    class RunnerStrategy(SearchStrategy):

        def do_draw(self, data):
            runner = getattr(data, 'hypothesis_runner', not_set)
            if runner is not_set:
                if default is not_set:
                    raise InvalidArgument(
                        'Cannot use runner() strategy with no '
                        'associated runner or explicit default.'
                    )
                else:
                    return default
            else:
                return runner
    return RunnerStrategy()


@cacheable
def data():
    """This isn't really a normal strategy, but instead gives you an object
    which can be used to draw data interactively from other strategies.

    It can only be used within :func:`@given <hypothesis.given>`, not
    :func:`find() <hypothesis.find>`. This is because the lifetime
    of the object cannot outlast the test body.

    See :ref:`the rest of the documentation <interactive-draw>` for more
    complete information.

    Examples from this strategy do not shrink (because there is only one),
    but the result of calls to each draw() call shrink as they normally would.

    """
    from hypothesis.control import note

    class DataObject(object):

        def __init__(self, data):
            self.count = 0
            self.data = data

        def __repr__(self):
            return 'data(...)'

        def draw(self, strategy, label=None):
            result = self.data.draw(strategy)
            self.count += 1
            if label is not None:
                note('Draw %d (%s): %r' % (self.count, label, result))
            else:
                note('Draw %d: %r' % (self.count, result))
            return result

    class DataStrategy(SearchStrategy):
        supports_find = False

        def do_draw(self, data):
            data.can_reproduce_example_from_repr = False

            if not hasattr(data, 'hypothesis_shared_data_strategy'):
                data.hypothesis_shared_data_strategy = DataObject(data)
            return data.hypothesis_shared_data_strategy

        def __repr__(self):
            return 'data()'

        def map(self, f):
            self.__not_a_first_class_strategy('map')

        def filter(self, f):
            self.__not_a_first_class_strategy('filter')

        def flatmap(self, f):
            self.__not_a_first_class_strategy('flatmap')

        def example(self):
            self.__not_a_first_class_strategy('example')

        def __not_a_first_class_strategy(self, name):
            raise InvalidArgument((
                'Cannot call %s on a DataStrategy. You should probably be '
                "using @composite for whatever it is you're trying to do."
            ) % (name,))
    return DataStrategy()


def register_type_strategy(custom_type, strategy):
    """Add an entry to the global type-to-strategy lookup.

    This lookup is used in :func:`~hypothesis.strategies.builds` and
    :func:`@given <hypothesis.given>`.

    :func:`~hypothesis.strategies.builds` will be used automatically for
    classes with type annotations on ``__init__`` , so you only need to
    register a strategy if one or more arguments need to be more tightly
    defined than their type-based default, or if you want to supply a strategy
    for an argument with a default value.

    ``strategy`` may be a search strategy, or a function that takes a type and
    returns a strategy (useful for generic types).

    """
    from hypothesis.searchstrategy import types
    if not isinstance(custom_type, type):
        raise InvalidArgument('custom_type=%r must be a type')
    elif not (isinstance(strategy, SearchStrategy) or callable(strategy)):
        raise InvalidArgument(
            'strategy=%r must be a SearchStrategy, or a function that takes '
            'a generic type and returns a specific SearchStrategy')
    elif isinstance(strategy, SearchStrategy) and strategy.is_empty:
        raise InvalidArgument('strategy=%r must not be empty')
    types._global_type_lookup[custom_type] = strategy
    from_type.__clear_cache()


@cacheable
def deferred(definition):
    """A deferred strategy allows you to write a strategy that references other
    strategies that have not yet been defined. This allows for the easy
    definition of recursive and mutually recursive strategies.

    The definition argument should be a zero-argument function that returns a
    strategy. It will be evaluated the first time the strategy is used to
    produce an example.

    Example usage:

    >>> import hypothesis.strategies as st
    >>> x = st.deferred(lambda: st.booleans() | st.tuples(x, x))
    >>> x.example()
    (((False, (True, True)), (False, True)), (True, True))
    >>> x.example()
    True

    Mutual recursion also works fine:

    >>> a = st.deferred(lambda: st.booleans() | b)
    >>> b = st.deferred(lambda: st.tuples(a, a))
    >>> a.example()
    True
    >>> b.example()
    (False, (False, ((False, True), False)))

    Examples from this strategy shrink as they normally would from the strategy
    returned by the definition.

    """
    from hypothesis.searchstrategy.deferred import DeferredStrategy
    return DeferredStrategy(definition)


assert _strategies.issubset(set(__all__)), _strategies - set(__all__)
