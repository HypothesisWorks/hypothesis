# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import operator
from collections import namedtuple

import numpy as np
from hypothesis import strategy
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.internal.compat import hrange, reduce, text_type, \
    binary_type
from hypothesis.searchstrategy.strategies import check_length, \
    check_data_type

ArrayDescription = namedtuple('ArrayDescription', ('dtype', 'shape'))


class ArrayStrategy(SearchStrategy):

    def __init__(self, element_strategy, shape, dtype):
        self.shape = tuple(shape)
        assert shape
        self.array_size = reduce(operator.mul, shape)
        self.dtype = dtype
        self.element_strategy = element_strategy

    def produce_parameter(self, random):
        return self.element_strategy.produce_parameter(random)

    def produce_template(self, context, parameter_value):
        result = tuple(
            self.element_strategy.produce_template(
                context, parameter_value
            )
            for i in hrange(self.array_size)
        )
        return result

    def simplifiers(self, random, template):
        assert isinstance(template, tuple)
        yield self.simplify_with_example_cloning
        yield self.shared_simplification(self.element_strategy.full_simplify)

        for i in self.indices_roughly_from_worst_to_best(random, template):
            yield self.simplifier_for_index(
                i, self.element_strategy.full_simplify)

    def simplifier_for_index(self, i, simplify):
        def accept(random, template):
            if i >= len(template):
                return
            replacement = list(template)
            for s in simplify(random, template[i]):
                replacement[i] = s
                yield tuple(replacement)
        accept.__name__ = str(
            'simplifier_for_index(%d, %s)' % (i, simplify.__name__)
        )
        return accept

    def strictly_simpler(self, x, y):
        for u, v in zip(x, y):
            if self.element_strategy.strictly_simpler(u, v):
                return True
            if self.element_strategy.strictly_simpler(v, u):
                return False
        return False

    def simplify_with_example_cloning(self, random, x):
        assert isinstance(x, tuple)
        if len(x) <= 1:
            return

        best = x[0]
        any_shrinks = False
        for t in x:
            if self.element_strategy.strictly_simpler(
                t, best
            ):
                any_shrinks = True
                best = t
            if not any_shrinks:
                any_shrinks = self.element_strategy.strictly_simpler(best, t)

        if any_shrinks:
            yield (best,) * len(x)

        for _ in hrange(20):
            result = list(x)
            pivot = random.choice(x)
            for _ in hrange(10):
                new_pivot = random.choice(x)
                if self.element_strategy.strictly_simpler(new_pivot, pivot):
                    pivot = new_pivot
            indices = [
                j for j in hrange(len(x))
                if self.element_strategy.strictly_simpler(pivot, x[j])]
            if not indices:
                break
            random.shuffle(indices)
            indices = indices[:random.randint(1, len(x) - 1)]
            for j in indices:
                result[j] = pivot
            yield tuple(result)

    def simplify_with_random_discards(self, random, x):
        assert isinstance(x, tuple)
        if len(x) <= 3:
            return

        for _ in hrange(10):
            results = []
            for t in x:
                if random.randint(0, 1):
                    results.append(t)
            yield tuple(results)

    def indices_roughly_from_worst_to_best(self, random, x):
        pivot = random.choice(x)
        bad = []
        good = []
        y = list(hrange(len(x)))
        random.shuffle(y)
        for t in y:
            if self.element_strategy.strictly_simpler(x[t], pivot):
                good.append(t)
            else:
                bad.append(t)
        return bad + good

    def shared_indices(self, random, template):
        same_valued_indices = {}
        for i, value in enumerate(template):
            same_valued_indices.setdefault(value, []).append(i)
        for indices in same_valued_indices.values():
            if len(indices) > 1:
                yield tuple(indices)
                if len(indices) > 2:
                    indices = list(indices)
                    random.shuffle(indices)
                    n = random.randint(2, len(indices))
                    yield tuple(indices[:n])

    def shared_simplification(self, simplify):
        def accept(random, x):
            sharing = list(self.shared_indices(random, x))
            if not sharing:
                return
            sharing.sort(key=len, reverse=True)

            for indices in sharing:
                value = x[indices[0]]
                for simpler in simplify(random, value):
                    copy = list(x)
                    for i in indices:
                        copy[i] = simpler
                    yield tuple(copy)
        accept.__name__ = str(
            'shared_simplification(%s)' % (simplify.__name__,)
        )
        return accept

    def to_basic(self, template):
        return list(map(self.element_strategy.to_basic, template))

    def from_basic(self, data):
        check_data_type(list, data)
        check_length(self.array_size, data)
        return (
            tuple(map(self.element_strategy.from_basic, data))
        )

    def reify(self, template):
        result = np.array([
            self.element_strategy.reify(t) for t in template
        ], dtype=self.dtype)
        return result.reshape(self.shape)


def arrays(specifier, shape):
    if isinstance(shape, int):
        shape = (shape,)
    if isinstance(specifier, (text_type, binary_type)):
        specifier = np.dtype(specifier)
    shape = tuple(shape)
    if not shape:
        dt = np.dtype(specifier)
        if dt.kind != 'O':
            return dt
        return specifier
    else:
        return ArrayDescription(specifier, shape)


@strategy.extend(ArrayDescription)
def array_strategy(specifier, settings):
    dtype = specifier.dtype
    if isinstance(dtype, (text_type, binary_type)):
        dtype = np.dtype(dtype)

    if not isinstance(dtype, np.dtype):
        dtype = np.dtype(dtype)
    if dtype.kind != 'O':
        typ = dtype
    else:
        typ = specifier.dtype

    return ArrayStrategy(
        shape=specifier.shape,
        dtype=dtype,
        element_strategy=strategy(typ, settings),
    )
