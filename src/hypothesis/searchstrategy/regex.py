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

import hypothesis.strategies as strats
from hypothesis.searchstrategy import SearchStrategy
from itertools import chain
import string
import sys
import re

def strategy_join(*strategies):
    return strats.builds(lambda *x: u"".join(x),*strategies)

#don't use very long examples
limit = 15

class RegexStrategy(SearchStrategy):
    """
    Strategy for generating strings conforming to a regular expression

    maybe there are problems with locales
    """
    def __init__(self,pattern):
        parsed = re.sre_parse.parse(pattern)
        self.cache = {}
        self.strategies = [self._handle_state(state) for state in parsed]

    def do_draw(self,data):
        self.cache = {}
        return u"".join(data.draw(strat) for strat in self.strategies)

    def _categories(self,category):
        if category == "category_digit":
            return string.digits
        elif category == "category_not_digit":
            return string.ascii_letters + string.punctuation
        elif category == "category_space":
            return string.whitespace
        elif category == "category_not_space":
            return string.printable.strip()
        elif category == "category_word":
            return string.ascii_letters + string.digits + '_'
        elif category == "category_not_word":
            return ''.join(set(string.printable)
                            .difference(string.ascii_letters +
                                        string.digits + '_'))

    def _handle_character_sets(self,state):
        opcode, value = state
        if opcode == "range":
            return [unichr(val) for val in xrange(value[0],value[1]+1)]
        elif opcode == "literal":
            return [unichr(value)]
        elif opcode == "category":
            return self._categories(value)
        else:
            print "Unknown opcode in handle_negated_state",opcode

    def _handle_state(self,state):
        """
        returns a strategy
        """
        opcode, value = state
        if opcode == "literal":
            return strats.just(unichr(value))
        elif opcode == "not_literal":
            return strats.characters(blacklist_characters=unichr(value))
        elif opcode == "at":
            return strats.just("")
        elif opcode == "in":
            if value[0][0] == "negate":
                candidates = []
                for v in value[1:]:
                    candidates.extend(chain(*(self._handle_character_sets(v))))
                return strats.characters(blacklist_characters=candidates)
            else:
                candidates = []
                for v in value:
                    candidates.extend(chain(*(self._handle_character_sets(v))))
                return strats.sampled_from(candidates)
        elif opcode == "any":
            return strats.characters()
        elif opcode == "range":
            return strats.integers(min_value=value[0],max_value=value[1]).map(unichr)
        elif opcode == "category":
            return strats.text(alphabet=categories(value),max_size=1,min_size=1)
        elif opcode == "branch":
            branches = []
            for branch in value[1]:
                strat_tuple = strats.tuples(*[self._handle_state(v) for v in branch])
                branches.append(strat_tuple.map(lambda x: u"".join(x)))
            return strats.one_of(branches)
        elif opcode == "subpattern":
            parts = []
            for part in value[1]:
                parts.append(self._handle_state(part))
            result = strats.tuples(*parts).map(lambda x: u"".join(x))
            if value[0]:
                self.cache[value[0]] = result
                result = strats.shared(result,key=value[0])
            return result
        elif opcode == "assert":
            return strats.just("")
        elif opcode == "assert_not":
            return strats.just("")
        elif opcode == "groupref":
            return strats.shared(self.cache[value],key=value)
        elif opcode == "min_repeat":
            start_range, end_range, val = value
            end_range = min((end_range, limit))
            result = []
            for v in val:
                part = strats.lists(
                    self._handle_state(v),
                    min_size=start_range,
                    max_size=end_range
                ).map(lambda x: u"".join(x))
                result.append(part)
            return strategy_join(*result)
        elif opcode == "max_repeat":
            start_range, end_range, val = value
            end_range = min((end_range, limit))
            result = []
            for v in val:
                part = strats.lists(
                    self._handle_state(v),
                    min_size=start_range,
                    max_size=end_range
                ).map(lambda x: u"".join(x))
                result.append(part)
            return strategy_join(*result)
        else:
            print "Unknown opcode",opcode, value
