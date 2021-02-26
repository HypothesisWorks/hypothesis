# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

import threading
from inspect import signature
from typing import Callable, Dict

from hypothesis.internal.cache import LRUReusedCache
from hypothesis.internal.floats import float_to_int
from hypothesis.internal.reflection import proxies
from hypothesis.strategies._internal.lazy import LazyStrategy
from hypothesis.strategies._internal.strategies import SearchStrategy, T

_strategies: Dict[str, Callable[..., SearchStrategy]] = {}


class FloatKey:
    def __init__(self, f):
        self.value = float_to_int(f)

    def __eq__(self, other):
        return isinstance(other, FloatKey) and (other.value == self.value)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.value)


def convert_value(v):
    if isinstance(v, float):
        return FloatKey(v)
    return (type(v), v)


_CACHE = threading.local()


def get_cache() -> LRUReusedCache:
    try:
        return _CACHE.STRATEGY_CACHE
    except AttributeError:
        _CACHE.STRATEGY_CACHE = LRUReusedCache(1024)
        return _CACHE.STRATEGY_CACHE


def clear_cache() -> None:
    cache = get_cache()
    cache.clear()


def cacheable(fn: T) -> T:
    @proxies(fn)
    def cached_strategy(*args, **kwargs):
        try:
            kwargs_cache_key = {(k, convert_value(v)) for k, v in kwargs.items()}
        except TypeError:
            return fn(*args, **kwargs)
        cache_key = (fn, tuple(map(convert_value, args)), frozenset(kwargs_cache_key))
        cache = get_cache()
        try:
            if cache_key in cache:
                return cache[cache_key]
        except TypeError:
            return fn(*args, **kwargs)
        else:
            result = fn(*args, **kwargs)
            if not isinstance(result, SearchStrategy) or result.is_cacheable:
                cache[cache_key] = result
            return result

    cached_strategy.__clear_cache = clear_cache
    return cached_strategy


def defines_strategy(
    *, force_reusable_values: bool = False, try_non_lazy: bool = False
) -> Callable[[T], T]:
    """Returns a decorator for strategy functions.

    If force_reusable is True, the generated values are assumed to be
    reusable, i.e. immutable and safe to cache, across multiple test
    invocations.

    If try_non_lazy is True, attempt to execute the strategy definition
    function immediately, so that a LazyStrategy is only returned if this
    raises an exception.
    """

    def decorator(strategy_definition):
        """A decorator that registers the function as a strategy and makes it
        lazily evaluated."""
        _strategies[strategy_definition.__name__] = signature(strategy_definition)

        @proxies(strategy_definition)
        def accept(*args, **kwargs):
            if try_non_lazy:
                # Why not try this unconditionally?  Because we'd end up with very
                # deep nesting of recursive strategies - better to be lazy unless we
                # *know* that eager evaluation is the right choice.
                try:
                    return strategy_definition(*args, **kwargs)
                except Exception:
                    # If invoking the strategy definition raises an exception,
                    # wrap that up in a LazyStrategy so it happens again later.
                    pass
            result = LazyStrategy(strategy_definition, args, kwargs)
            if force_reusable_values:
                result.force_has_reusable_values = True
                assert result.has_reusable_values
            return result

        accept.is_hypothesis_strategy_function = True
        return accept

    return decorator
