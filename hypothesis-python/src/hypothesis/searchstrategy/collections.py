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
from hypothesis.internal.compat import OrderedDict
from hypothesis.searchstrategy.misc import SampledFromStrategy
from hypothesis.internal.conjecture.utils import integer_range, \
    combine_labels, calc_label_from_name
from hypothesis.searchstrategy.strategies import SearchStrategy, \
    MappedSearchStrategy

UNIQUE_ELEM_LABEL = calc_label_from_name('a unique index')


class TupleStrategy(SearchStrategy):
    """A strategy responsible for fixed length tuples based on heterogenous
    strategies for each of their elements."""

    def __init__(self, strategies):
        SearchStrategy.__init__(self)
        self.element_strategies = tuple(strategies)

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
        return 'TupleStrategy((%s))' % (tuple_string,)

    def calc_has_reusable_values(self, recur):
        return all(recur(e) for e in self.element_strategies)

    def do_draw(self, data):
        return tuple(data.draw(e) for e in self.element_strategies)

    def calc_is_empty(self, recur):
        return any(recur(e) for e in self.element_strategies)


class ListStrategy(SearchStrategy):
    """A strategy for lists which takes a strategy for its elements and the
    allowed lengths, and generates lists with the correct size and contents."""

    def __init__(self, elements, min_size=0, max_size=float('inf')):
        SearchStrategy.__init__(self)
        self.min_size = min_size or 0
        self.max_size = max_size if max_size is not None else float('inf')
        assert 0 <= self.min_size <= self.max_size
        self.average_size = min(
            max(self.min_size * 2, self.min_size + 5),
            0.5 * (self.min_size + self.max_size),
        )
        self.element_strategy = elements

    def calc_label(self):
        return combine_labels(self.class_label, self.element_strategy.label)

    def do_validate(self):
        self.element_strategy.validate()
        if self.is_empty:
            raise InvalidArgument((
                'Cannot create non-empty lists with elements drawn from '
                'strategy %r because it has no values.') % (
                self.element_strategy,))
        if self.element_strategy.is_empty and 0 < self.max_size < float('inf'):
            from hypothesis._settings import note_deprecation
            note_deprecation(
                'Cannot create a collection of max_size=%r, because no '
                'elements can be drawn from the element strategy %r'
                % (self.max_size, self.element_strategy)
            )

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
        result = []
        while elements.more():
            result.append(data.draw(self.element_strategy))
        return result

    def __repr__(self):
        return '%s(%r, min_size=%r, max_size=%r)' % (
            self.__class__.__name__, self.element_strategy, self.min_size,
            self.max_size
        )


class UniqueListStrategy(ListStrategy):

    def __init__(self, elements, min_size, max_size, key):
        self.values = None
        if isinstance(elements, SampledFromStrategy):
            self.values = []
            seen = set()
            for x in elements.elements:
                if key(x) not in seen:
                    self.values.append(x)
                    seen.add(key(x))
            if len(self.values) < (min_size or 0):
                # If no draw is possible, use the normal logic.
                self.values = None
            elif max_size is not None:
                max_size = min(max_size, len(self.values))
        super(UniqueListStrategy, self).__init__(elements, min_size, max_size)
        self.key = key

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

        if self.values is not None:
            # With a known and perhaps small set of elements, we have two
            # tricks to reduce the rate of early exits from rejection
            # sampling.  (1) pre-filter down to unique elements in __init__.
            # (2) nested retries, marking the discards for the shrinker.
            while elements.more():
                for _ in range(8):
                    data.start_example(UNIQUE_ELEM_LABEL)
                    idx = integer_range(data, 0, len(self.values) - 1)
                    data.stop_example(discard=idx in seen)
                    if idx not in seen:
                        seen.add(idx)
                        result.append(self.values[idx])
                        break
                else:
                    elements.reject()
            assert self.max_size >= len(result) >= self.min_size
            return result

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
                (strategy_dict[k] for k in self.keys)
            )
        )

    def calc_is_empty(self, recur):
        return recur(self.mapped_strategy)

    def __repr__(self):
        return 'FixedKeysDictStrategy(%r, %r)' % (
            self.keys, self.mapped_strategy)

    def pack(self, value):
        return self.dict_type(zip(self.keys, value))
