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

import hypothesis.internal.conjecture.utils as cu
from hypothesis.errors import InvalidArgument
from hypothesis.internal.compat import OrderedDict, hbytes
from hypothesis.searchstrategy.strategies import SearchStrategy, \
    MappedSearchStrategy, combine_labels, one_of_strategies


class TupleStrategy(SearchStrategy):
    """A strategy responsible for fixed length tuples based on heterogenous
    strategies for each of their elements."""

    def __init__(self,
                 strategies, tuple_type):
        SearchStrategy.__init__(self)
        strategies = tuple(strategies)
        self.element_strategies = strategies

    def do_validate(self):
        for s in self.element_strategies:
            s.validate()

    def calc_label(self):
        return combine_labels(
            self.class_label, *[s.label for s in self.element_strategies])

    def __repr__(self):
        if len(self.element_strategies) == 1:
            tuple_string = '%s,' % (repr(self.element_strategies[0]),)
        else:
            tuple_string = ', '.join(map(repr, self.element_strategies))
        return 'TupleStrategy((%s))' % (
            tuple_string,
        )

    def calc_has_reusable_values(self, recur):
        return all(recur(e) for e in self.element_strategies)

    def newtuple(self, xs):
        """Produce a new tuple of the correct type."""
        return tuple(xs)

    def do_draw(self, data):
        return self.newtuple(
            data.draw(e) for e in self.element_strategies
        )

    def calc_is_empty(self, recur):
        return any(recur(e) for e in self.element_strategies)


TERMINATOR = hbytes(b'\0')


class ListStrategy(SearchStrategy):
    """A strategy for lists which takes an intended average length and a
    strategy for each of its element types and generates lists containing any
    of those element types.

    The conditional distribution of the length is geometric, and the
    conditional distribution of each parameter is whatever their
    strategies define.

    """

    def __init__(
        self,
        strategies, average_length=50.0, min_size=0, max_size=float('inf')
    ):
        SearchStrategy.__init__(self)

        assert average_length > 0
        self.average_length = average_length
        strategies = tuple(strategies)
        self.min_size = min_size or 0
        self.max_size = max_size or float('inf')
        self.element_strategy = one_of_strategies(strategies)

    def calc_label(self):
        return combine_labels(self.class_label, self.element_strategy.label)

    def do_validate(self):
        self.element_strategy.validate()
        if self.is_empty:
            raise InvalidArgument((
                'Cannot create non-empty lists with elements drawn from '
                'strategy %r because it has no values.') % (
                self.element_strategy,))

    def calc_is_empty(self, recur):
        if self.min_size == 0:
            return False
        else:
            return recur(self.element_strategy)

    def do_draw(self, data):
        if self.element_strategy.is_empty:
            assert self.min_size == 0
            return []

        elements = cu.many(
            data,
            min_size=self.min_size, max_size=self.max_size,
            average_size=self.average_length
        )
        result = []
        while elements.more():
            result.append(data.draw(self.element_strategy))
        return result

    def __repr__(self):
        return (
            'ListStrategy(%r, min_size=%r, average_size=%r, max_size=%r)'
        ) % (
            self.element_strategy, self.min_size, self.average_length,
            self.max_size
        )


class UniqueListStrategy(SearchStrategy):

    def __init__(
        self,
        elements, min_size, max_size, average_size,
        key
    ):
        super(UniqueListStrategy, self).__init__()
        assert min_size <= average_size <= max_size
        self.min_size = min_size
        self.max_size = max_size
        self.average_size = average_size
        self.element_strategy = elements
        self.key = key

    def do_validate(self):
        self.element_strategy.validate()
        if self.is_empty:
            raise InvalidArgument((
                'Cannot create non-empty lists with elements drawn from '
                'strategy %r because it has no values.') % (
                self.element_strategy,))

    def calc_is_empty(self, recur):
        if self.min_size == 0:
            return False
        else:
            return recur(self.element_strategy)

    def do_draw(self, data):
        if self.element_strategy.is_empty:
            assert self.min_size == 0
            return []

        elements = cu.many(
            data,
            min_size=self.min_size, max_size=self.max_size,
            average_size=self.average_size
        )
        seen = set()
        result = []

        while elements.more():
            value = data.draw(self.element_strategy)
            k = self.key(value)
            if k in seen:
                elements.reject()
            else:
                seen.add(k)
                result.append(value)
        assert self.max_size >= len(result) >= self.min_size
        return result


class FixedKeysDictStrategy(MappedSearchStrategy):
    """A strategy which produces dicts with a fixed set of keys, given a
    strategy for each of their equivalent values.

    e.g. {'foo' : some_int_strategy} would generate dicts with the single
    key 'foo' mapping to some integer.

    """

    def __init__(self, strategy_dict):
        self.dict_type = type(strategy_dict)

        if isinstance(strategy_dict, OrderedDict):
            self.keys = tuple(strategy_dict.keys())
        else:
            try:
                self.keys = tuple(sorted(
                    strategy_dict.keys(),
                ))
            except TypeError:
                self.keys = tuple(sorted(
                    strategy_dict.keys(), key=repr,
                ))
        super(FixedKeysDictStrategy, self).__init__(
            strategy=TupleStrategy(
                (strategy_dict[k] for k in self.keys), tuple
            )
        )

    def calc_is_empty(self, recur):
        return recur(self.mapped_strategy)

    def __repr__(self):
        return 'FixedKeysDictStrategy(%r, %r)' % (
            self.keys, self.mapped_strategy)

    def pack(self, value):
        return self.dict_type(zip(self.keys, value))
