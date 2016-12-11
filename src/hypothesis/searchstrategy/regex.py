# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2016 David R. MacIver
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

import re
import sys
import string
from itertools import chain

import hypothesis.strategies as strats
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.internal.compat import hunichr, hrange


def strategy_concat(strategies):
    """given a list of strategies yielding strings return a strategy yielding
    their concatenation."""
    return strats.tuples(*strategies).map(lambda x: u"".join(x))


class RegexStrategy(SearchStrategy):
    """Strategy for generating strings matching a regular expression.

    Currently does not support \B, positive and negative lookbehind
    assertions and conditional matching.

    """

    def __init__(self, pattern):
        parsed = re.sre_parse.parse(pattern)
        self.cache = {}
        self.strategies = [self._handle_state(state) for state in parsed]

    def do_draw(self, data):
        self.cache = {}
        return u"".join(data.draw(strat) for strat in self.strategies)

    def _categories(self, category):
        if category == 'category_digit':
            return string.digits
        elif category == 'category_not_digit':
            return string.ascii_letters + string.punctuation
        elif category == 'category_space':
            return string.whitespace
        elif category == 'category_not_space':
            return string.printable.strip()
        elif category == 'category_word':
            return string.ascii_letters + string.digits + '_'
        elif category == 'category_not_word':
            return ''.join(set(string.printable)
                           .difference(string.ascii_letters +
                                       string.digits + '_'))
        else:
            raise NotImplementedError

    def _handle_character_sets(self, state):
        opcode, value = state
        if opcode == 'range':
            return [hunichr(val) for val in hrange(value[0], value[1] + 1)]
        elif opcode == 'literal':
            return [hunichr(value)]
        elif opcode == 'category':
            return self._categories(value)
        else:
            raise NotImplementedError

    def _handle_state(self, state):
        opcode, value = state
        if opcode == 'literal':
            return strats.just(hunichr(value))
        elif opcode == 'not_literal':
            return strats.characters(blacklist_characters=hunichr(value))
        elif opcode == 'at':
            return strats.just('')
        elif opcode == 'in':
            if value[0][0] == 'negate':
                candidates = []
                for v in value[1:]:
                    candidates.extend(chain(*(self._handle_character_sets(v))))
                return strats.characters(blacklist_characters=candidates)
            else:
                candidates = []
                for v in value:
                    candidates.extend(chain(*(self._handle_character_sets(v))))
                return strats.sampled_from(candidates)
        elif opcode == 'any':
            return strats.characters()
        elif opcode == 'branch':
            branches = []
            for val in value[1]:
                branch = [self._handle_state(v) for v in val]
                branches.append(strategy_concat(branch))
            return strats.one_of(branches)
        elif opcode == 'subpattern':
            parts = []
            for part in value[1]:
                parts.append(self._handle_state(part))
            result = strategy_concat(parts)
            if value[0]:
                self.cache[value[0]] = result
                result = strats.shared(result, key=value[0])
            return result
        elif opcode == 'assert':
            result = []
            for part in value[1]:
                result.append(self._handle_state(part))
            return strategy_concat(result)
        elif opcode == 'assert_not':
            return strats.just('')
        elif opcode == 'groupref':
            return strats.shared(self.cache[value], key=value)
        elif opcode == 'min_repeat':
            start_range, end_range, val = value
            result = []
            for v in val:
                part = strats.lists(
                    self._handle_state(v),
                    min_size=start_range,
                    max_size=end_range
                ).map(lambda x: u"".join(x))
                result.append(part)
            return strategy_concat(result)
        elif opcode == 'max_repeat':
            start_range, end_range, val = value
            result = []
            for v in val:
                part = strats.lists(
                    self._handle_state(v),
                    min_size=start_range,
                    max_size=end_range
                ).map(lambda x: u"".join(x))
                result.append(part)
            return strats.tuples(*result).map(lambda x: u"".join(x))
        else:
            raise NotImplementedError(opcode)
