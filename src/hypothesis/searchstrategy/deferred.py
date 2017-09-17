# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

import inspect

from hypothesis.errors import InvalidArgument
from hypothesis.internal.reflection import get_pretty_function_description
from hypothesis.searchstrategy.strategies import SearchStrategy


class DeferredStrategy(SearchStrategy):

    """A strategy which may be used before it is fully defined."""

    def __init__(self, definition):
        SearchStrategy.__init__(self)
        self.__wrapped_strategy = None
        self.__in_repr = False
        self.__is_empty = None
        self.__definition = definition

    @property
    def wrapped_strategy(self):
        if self.__wrapped_strategy is None:
            if not inspect.isfunction(self.__definition):
                raise InvalidArgument((
                    'Excepted a definition to be a function but got %r of type'
                    ' %s instead.') % (
                        self.__definition, type(self.__definition).__name__))
            result = self.__definition()
            if result is self:
                raise InvalidArgument(
                    'Cannot define a deferred strategy to be itself')
            if not isinstance(result, SearchStrategy):
                raise InvalidArgument((
                    'Expected definition to return a SearchStrategy but '
                    'returned %r of type %s') % (
                        result, type(result).__name__
                ))
            self.__wrapped_strategy = result
            del self.__definition
        return self.__wrapped_strategy

    @property
    def branches(self):
        return self.wrapped_strategy.branches

    @property
    def supports_find(self):
        return self.wrapped_strategy.supports_find

    def calc_is_empty(self, recur):
        return recur(self.wrapped_strategy)

    def calc_has_reusable_values(self, recur):
        return recur(self.wrapped_strategy)

    def __repr__(self):
        if self.__wrapped_strategy is not None:
            if self.__in_repr:
                return '(deferred@%r)' % (id(self),)
            try:
                self.__in_repr = True
                return repr(self.__wrapped_strategy)
            finally:
                self.__in_repr = False
        else:
            return 'deferred(%s)' % (
                get_pretty_function_description(self.__definition)
            )

    def do_draw(self, data):
        return data.draw(self.wrapped_strategy)
