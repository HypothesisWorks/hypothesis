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

from random import Random
from weakref import WeakKeyDictionary

from hypothesis import assume
from hypothesis.errors import BadTemplateDraw
from hypothesis.control import cleanup
from hypothesis.internal.compat import text_type, integer_types
from hypothesis.utils.conventions import not_set
from hypothesis.searchstrategy.strategies import BadData, check_length, \
    SearchStrategy, check_data_type


class MorpherParameter(object):

    def __init__(self, seed):
        self.seed = seed
        self.cache = WeakKeyDictionary()

    def parameter(self, strategy):
        try:
            return self.cache[strategy]
        except KeyError:
            pass
        self.cache[strategy] = strategy.draw_parameter(Random(self.seed))
        return self.cache[strategy]


class Morpher(object):

    def __init__(self, parameter, template_seed, data=not_set):
        assert isinstance(parameter, MorpherParameter)
        self.parameter = parameter
        self.template_seed = template_seed
        self.data = data
        self.last_strategy = None
        self.last_template = not_set

    def __eq__(self, other):
        return isinstance(other, Morpher) and (
            self.parameter.seed == other.parameter.seed and
            self.template_seed == other.template_seed and
            self.data == other.data
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.parameter.seed) ^ hash(self.template_seed)

    def __copy__(self):
        return Morpher(self.parameter, self.template_seed, self.data)

    def __deepcopy__(self, table):
        return self.__copy__()

    def become(self, strategy):
        if strategy is self.last_strategy:
            template = self.last_template
        else:
            template = not_set
            if self.data is not not_set:
                try:
                    template = strategy.from_basic(self.data)
                except BadData:
                    assume(False)
            else:
                rnd = Random(self.template_seed)
                try:
                    template = strategy.draw_template(
                        rnd,
                        self.parameter.parameter(strategy),
                    )
                except BadTemplateDraw:
                    assume(False)
                self.data = strategy.to_basic(template)
        self.last_strategy = strategy
        self.last_template = template
        return strategy.reify(template)

    def __trackas__(self):
        result = [self.parameter.seed, self.template_seed]
        if self.last_template is not not_set:
            result.append(self.last_template)
        else:
            result.append(None)
        if self.data is not not_set:
            result.append(self.data)
        else:
            result.append(None)
        return result

    def __repr__(self):
        return u'Morpher(%d, %d, %r)' % (
            self.parameter.seed, self.template_seed, self.data)


def _basic_cost(data):
    if isinstance(data, list):
        return sum(_basic_cost(d) for d in data) + 1
    elif isinstance(data, text_type):
        return len(data) + 1
    else:
        return 1


class MorpherStrategy(SearchStrategy):

    def draw_parameter(self, random):
        return MorpherParameter(random.getrandbits(64))

    def draw_template(self, random, parameter):
        return Morpher(
            parameter=parameter,
            template_seed=random.getrandbits(64),
        )

    def reify(self, template):
        def write_back():
            s = template.last_strategy
            if s is not None:
                template.data = template.last_strategy.to_basic(
                    template.last_template
                )
        cleanup(write_back)
        return template

    def strictly_simpler(self, x, y):
        if x.data is not_set and y.data is not_set:
            return x.template_seed < y.template_seed
        if x.data is not_set:
            return False
        if y.data is not_set:
            return True
        return _basic_cost(x.data) < _basic_cost(y.data)

    def simplifiers(self, random, morpher):
        strategy = morpher.last_strategy
        if strategy is not None:
            for simplifier in strategy.simplifiers(
                random, morpher.last_template
            ):
                yield self.convert_simplifier(strategy, simplifier)

    def convert_simplifier(self, strategy, simplifier):
        def accept(random, morpher):
            morpher = morpher.__copy__()
            try:
                template = strategy.from_basic(morpher.data)
            # This case is almost impossible to hit reliably.
            except BadData:  # pragma: no cover
                return
            for simpler in simplifier(random, template):
                m = Morpher(
                    morpher.parameter, morpher.template_seed,
                    strategy.to_basic(simpler),
                )
                m.last_strategy = strategy
                m.last_template = simpler
                yield m
        accept.__name__ = str(
            u'convert_simplifier(..., %s)' % (simplifier.__name__,)
        )
        return accept

    def from_basic(self, data):
        check_data_type(list, data)
        if len(data) == 2:
            check_data_type(integer_types, data[0])
            check_data_type(integer_types, data[1])
            return Morpher(
                parameter=MorpherParameter(data[0]),
                template_seed=data[1])
        else:
            check_length(3, data)
            check_data_type(integer_types, data[0])
            check_data_type(integer_types, data[1])
            return Morpher(
                parameter=MorpherParameter(data[0]),
                template_seed=data[1], data=data[2])

    def to_basic(self, template):
        result = [template.parameter.seed, template.template_seed]
        if template.data is not not_set:
            result.append(template.data)
        return result
