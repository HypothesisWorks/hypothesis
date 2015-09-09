# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

from copy import copy
from random import Random

from hypothesis.errors import BadTemplateDraw, InvalidArgument
from hypothesis.control import cleanup
from hypothesis.internal.compat import integer_types
from hypothesis.searchstrategy.strategies import BadData, check_length, \
    SearchStrategy, check_data_type


class Morpher(object):

    def __init__(self, parameter_seed, template_seed, data=None):
        self.parameter_seed = parameter_seed
        self.template_seed = template_seed
        self.data = list(data or ())
        self.current_template = None
        self.current_index = -1
        self.current_strategy = None
        self.a_strategy = None

    def clear(self):
        self.flush()
        self.current_template = None
        self.current_index = -1
        self.current_strategy = None

    def flush(self):
        if self.current_index >= 0:
            self.data[self.current_index] = self.current_strategy.to_basic(
                self.current_template
            )

    def install(self, strategy):
        if self.current_strategy is not None:
            raise InvalidArgument(
                u'Cannot install multiple strategies into a morpher')
        self.a_strategy = strategy
        self.current_strategy = strategy
        for i, data in enumerate(self.data):
            try:
                self.current_template = strategy.from_basic(data)
                self.current_index = i
                return
            except BadData:
                pass
        parameter_random = Random(self.parameter_seed)
        template_random = Random(self.template_seed)
        while True:
            try:
                parameter = strategy.draw_parameter(parameter_random)
                template = strategy.draw_template(
                    template_random, parameter)
                break
            except BadTemplateDraw:
                pass
        basic = strategy.to_basic(template)
        self.data.append(basic)
        self.current_template = strategy.from_basic(basic)
        self.current_index = len(self.data) - 1

    def become(self, strategy):
        self.install(strategy)
        return strategy.reify(self.current_template)

    def __eq__(self, other):
        return isinstance(other, Morpher) and (
            self.parameter_seed == other.parameter_seed and
            self.template_seed == other.template_seed and
            self.data == other.data
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.parameter_seed) ^ hash(self.template_seed)

    def __copy__(self):
        result = self.clean_slate()
        if self.current_strategy is not None:
            result.install(self.current_strategy)
        return result

    def __deepcopy__(self, table):
        return self.__copy__()

    def clean_slate(self):
        return Morpher(
            self.parameter_seed, self.template_seed, self.data)

    def __trackas__(self):
        if self.current_strategy is not None:
            return [0, self.current_template]
        else:
            return [
                1,
                self.parameter_seed, self.template_seed,
                self.data,
            ]

    def __repr__(self):
        return u'Morpher(%d, %d, %r)' % (
            self.parameter_seed, self.template_seed, self.data)


class MorpherStrategy(SearchStrategy):

    def draw_parameter(self, random):
        return random.getrandbits(64)

    def draw_template(self, random, parameter):
        return Morpher(
            parameter_seed=parameter,
            template_seed=random.getrandbits(64),
        )

    def reify(self, template):
        strategy = template.current_strategy

        def fix_morpher_in_response_to_changes():
            if strategy is not None and template.current_strategy is None:
                template.install(strategy)
            else:
                template.flush()
        cleanup(fix_morpher_in_response_to_changes)
        template.clear()
        return template

    def strictly_simpler(self, x, y):
        if x.current_strategy is None:
            if y.current_strategy is None:
                return x.template_seed < y.template_seed
            else:
                return False
        else:
            if y.current_strategy is None:
                return True
            elif x.current_strategy is y.current_strategy:
                return x.current_strategy.strictly_simpler(
                    x.current_template, y.current_template
                )
            else:
                for s in (x.current_strategy, y.current_strategy):
                    xs = x.clean_slate()
                    ys = y.clean_slate()
                    xs.install(s)
                    ys.install(s)
                    xt = xs.current_template
                    yt = ys.current_template
                    if not s.strictly_simpler(xt, yt):
                        return False
                return True

    def simplifiers(self, random, morpher):
        strategy = morpher.a_strategy
        if strategy is not None:
            for simplifier in strategy.simplifiers(
                random, morpher.current_template
            ):
                yield self.convert_simplifier(strategy, simplifier)

    def convert_simplifier(self, strategy, simplifier):
        def accept(random, morpher):
            target = morpher.clean_slate()
            target.install(strategy)
            template = target.current_template
            for simpler in simplifier(random, template):
                new_template = copy(target)
                i = new_template.current_index
                assert i >= 0
                d = new_template.data
                d[i] = strategy.to_basic(simpler)
                d[i], d[0] = d[0], d[i]
                new_template.current_index = 0
                new_template.current_template = simpler
                yield new_template
        accept.__name__ = str(
            u'convert_simplifier(..., %s)' % (simplifier.__name__,)
        )
        return accept

    def from_basic(self, data):
        check_length(3, data)
        check_data_type(integer_types, data[0])
        check_data_type(integer_types, data[1])
        check_data_type(list, data[2])
        return Morpher(
            parameter_seed=data[0], template_seed=data[1], data=data[2])

    def to_basic(self, template):
        template = template.clean_slate()
        return [template.parameter_seed, template.template_seed, template.data]
