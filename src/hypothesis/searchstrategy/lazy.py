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

from hypothesis.internal.compat import getfullargspec
from hypothesis.internal.reflection import arg_string, \
    convert_keyword_arguments, convert_positional_arguments
from hypothesis.searchstrategy.strategies import SearchStrategy

unwrap_cache = {}
unwrap_depth = 0


def unwrap_strategies(s):
    global unwrap_depth

    if not isinstance(s, SearchStrategy):
        return s
    try:
        return unwrap_cache[s]
    except KeyError:
        pass

    unwrap_cache[s] = s

    try:
        unwrap_depth += 1
        try:
            result = unwrap_strategies(s.wrapped_strategy)
            unwrap_cache[s] = result
            try:
                assert result.force_has_reusable_values == \
                    s.force_has_reusable_values
            except AttributeError:
                pass

            try:
                result.force_has_reusable_values = s.force_has_reusable_values
            except AttributeError:
                pass
            return result
        except AttributeError:
            return s
    finally:
        unwrap_depth -= 1
        if unwrap_depth <= 0:
            unwrap_cache.clear()
        assert unwrap_depth >= 0


class LazyStrategy(SearchStrategy):
    """A strategy which is defined purely by conversion to and from another
    strategy.

    Its parameter and distribution come from that other strategy.

    """

    def __init__(self, function, args, kwargs):
        SearchStrategy.__init__(self)
        self.__wrapped_strategy = None
        self.__representation = None
        self.__function = function
        self.__args = args
        self.__kwargs = kwargs

    @property
    def supports_find(self):
        return self.wrapped_strategy.supports_find

    def calc_is_empty(self, recur):
        return recur(self.wrapped_strategy)

    def calc_has_reusable_values(self, recur):
        return recur(self.wrapped_strategy)

    def calc_is_cacheable(self, recur):
        for source in (self.__args, self.__kwargs.values()):
            for v in source:
                if isinstance(v, SearchStrategy) and not v.is_cacheable:
                    return False
        return True

    @property
    def wrapped_strategy(self):
        if self.__wrapped_strategy is None:
            unwrapped_args = tuple(
                unwrap_strategies(s) for s in self.__args)
            unwrapped_kwargs = {
                k: unwrap_strategies(v)
                for k, v in self.__kwargs.items()
            }

            base = self.__function(
                *self.__args, **self.__kwargs
            )
            if (
                unwrapped_args == self.__args and
                unwrapped_kwargs == self.__kwargs
            ):
                self.__wrapped_strategy = base
            else:
                self.__wrapped_strategy = self.__function(
                    *unwrapped_args,
                    **unwrapped_kwargs)
        return self.__wrapped_strategy

    def do_validate(self):
        w = self.wrapped_strategy
        assert isinstance(w, SearchStrategy), \
            '%r returned non-strategy %r' % (self, w)
        w.validate()

    def __repr__(self):
        if self.__representation is None:
            _args = self.__args
            _kwargs = self.__kwargs
            argspec = getfullargspec(self.__function)
            defaults = dict(argspec.kwonlydefaults or {})
            if argspec.defaults is not None:
                for name, value in zip(reversed(argspec.args),
                                       reversed(argspec.defaults)):
                    defaults[name] = value
            if len(argspec.args) > 1 or argspec.defaults:
                _args, _kwargs = convert_positional_arguments(
                    self.__function, _args, _kwargs)
            else:
                _args, _kwargs = convert_keyword_arguments(
                    self.__function, _args, _kwargs)
            kwargs_for_repr = dict(_kwargs)
            for k, v in defaults.items():
                if k in kwargs_for_repr and kwargs_for_repr[k] is defaults[k]:
                    del kwargs_for_repr[k]
            self.__representation = '%s(%s)' % (
                self.__function.__name__,
                arg_string(
                    self.__function, _args, kwargs_for_repr, reorder=False),
            )
        return self.__representation

    def do_draw(self, data):
        return data.draw(self.wrapped_strategy)

    @property
    def label(self):
        return self.wrapped_strategy.label
