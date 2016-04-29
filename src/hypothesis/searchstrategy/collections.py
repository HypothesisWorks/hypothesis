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

from collections import namedtuple

import hypothesis.internal.conjecture.utils as cu
from hypothesis.control import assume
from hypothesis.internal.compat import OrderedDict
from hypothesis.searchstrategy.strategies import SearchStrategy, \
    one_of_strategies, MappedSearchStrategy


class TupleStrategy(SearchStrategy):

    """A strategy responsible for fixed length tuples based on heterogenous
    strategies for each of their elements.

    This also handles namedtuples

    """

    def __init__(self,
                 strategies, tuple_type):
        SearchStrategy.__init__(self)
        strategies = tuple(strategies)
        self.element_strategies = strategies

    def validate(self):
        for s in self.element_strategies:
            s.validate()

    def __repr__(self):
        if len(self.element_strategies) == 1:
            tuple_string = '%s,' % (repr(self.element_strategies[0]),)
        else:
            tuple_string = ', '.join(map(repr, self.element_strategies))
        return 'TupleStrategy((%s))' % (
            tuple_string,
        )

    def newtuple(self, xs):
        """Produce a new tuple of the correct type."""
        return tuple(xs)

    def do_draw(self, data):
        return self.newtuple(
            data.draw(e) for e in self.element_strategies
        )


class ListStrategy(SearchStrategy):

    """A strategy for lists which takes an intended average length and a
    strategy for each of its element types and generates lists containing any
    of those element types.

    The conditional distribution of the length is geometric, and the
    conditional distribution of each parameter is whatever their
    strategies define.

    """

    Parameter = namedtuple(
        'Parameter', ('child_parameter', 'average_length')
    )

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

    def validate(self):
        self.element_strategy.validate()

    def do_draw(self, data):
        if self.max_size == self.min_size:
            return [
                data.draw(self.element_strategy)
                for _ in range(self.min_size)
            ]

        stopping_value = 1 - 1.0 / (1 + self.average_length)
        result = []
        while len(result) < self.max_size:
            data.start_example()
            more = cu.biased_coin(data, stopping_value)
            if not more:
                data.stop_example()
                if len(result) < self.min_size:
                    continue
                else:
                    break
            value = data.draw(self.element_strategy)
            data.stop_example()
            result.append(value)
        else:
            cu.write(data, b'\0')
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

    def validate(self):
        self.element_strategy.validate()

    Parameter = namedtuple(
        'Parameter', ('parameter_seed', 'parameter')
    )

    def do_draw(self, data):
        seen = set()
        result = []
        if self.max_size == self.min_size:
            while len(result) < self.max_size:
                v = data.draw(self.element_strategy)
                k = self.key(v)
                if k not in seen:
                    result.append(v)
                    seen.add(k)
            return result

        stopping_value = 1 - 1.0 / (1 + self.average_size)
        duplicates = 0
        while len(result) < self.max_size:
            data.start_example()
            if len(result) >= self.min_size:
                more = cu.biased_coin(data, stopping_value)
            else:
                more = True
            if not more:
                data.stop_example()
                break
            value = data.draw(self.element_strategy)
            data.stop_example()
            k = self.key(value)
            if k in seen:
                duplicates += 1
                assume(duplicates <= len(result))
                continue
            seen.add(k)
            result.append(value)
        assume(len(result) >= self.min_size)
        return result


class FixedKeysDictStrategy(MappedSearchStrategy):

    """A strategy which produces dicts with a fixed set of keys, given a
    strategy for each of their equivalent values.

    e.g. {'foo' : some_int_strategy} would
    generate dicts with the single key 'foo' mapping to some integer.

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

    def __repr__(self):
        return 'FixedKeysDictStrategy(%r, %r)' % (
            self.keys, self.mapped_strategy)

    def pack(self, value):
        return self.dict_type(zip(self.keys, value))
