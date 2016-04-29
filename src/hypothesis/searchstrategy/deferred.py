# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

from hypothesis import settings
from hypothesis.internal.compat import hrange, getargspec
from hypothesis.internal.reflection import arg_string, \
    convert_keyword_arguments, convert_positional_arguments
from hypothesis.searchstrategy.strategies import SearchStrategy


def tupleize(x):
    if isinstance(x, (tuple, list)):
        return tuple(x)
    else:
        return x


class DeferredStrategy(SearchStrategy):

    """A strategy which is defined purely by conversion to and from another
    strategy.

    Its parameter and distribution come from that other strategy.

    """

    def __init__(self, function, args, kwargs):
        SearchStrategy.__init__(self)
        self.__wrapped_strategy = None
        self.__representation = None
        self.__function = function
        self.__args = tuple(map(tupleize, args))
        self.__kwargs = dict(
            (k, tupleize(v)) for k, v in kwargs.items()
        )
        self.__settings = settings.default or settings()

    @property
    def supports_find(self):
        return self.wrapped_strategy.supports_find

    @property
    def is_empty(self):
        return self.wrapped_strategy.is_empty

    @property
    def wrapped_strategy(self):
        if self.__wrapped_strategy is None:
            with self.__settings:
                self.__wrapped_strategy = self.__function(
                    *self.__args,
                    **self.__kwargs
                )
        return self.__wrapped_strategy

    def validate(self):
        w = self.wrapped_strategy
        assert isinstance(w, SearchStrategy), \
            '%r returned non-strategy %r' % (self, w)
        w.validate()

    def __repr__(self):
        if self.__representation is None:
            _args = self.__args
            _kwargs = self.__kwargs
            argspec = getargspec(self.__function)
            defaults = {}
            if argspec.defaults is not None:
                for k in hrange(1, len(argspec.defaults) + 1):
                    defaults[argspec.args[-k]] = argspec.defaults[-k]
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
