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

"""
Idea shamelessly stolen from https://github.com/crdoconnor/xeger
who stole it from https://bitbucket.org/leapfrogdevelopment/rstr/
who stole it from http://code.google.com/p/xeger/
"""

from __future__ import division, print_function, absolute_import

import re
import sys
import string
from itertools import chain
import hypothesis.strategies as st

# Python 2/3 compatibility
if sys.version_info[0] >= 3:
    unichr = chr
    xrange = range
    basestring = str

# Strategy producing a character from the provided string
from_string = lambda x: st.sampled_from(list(x))

# Strategy joining strings produced by the provided strategies
@st.composite
def join(draw, strategies):
    return ''.join(draw(s) for s in strategies)

# Strategy drawing multiple repeat strings from one strategy
@st.composite
def repeat(draw, strategy, mn, mx):
    return ''.join(draw(st.lists(elements=strategy, min_size=mn, max_size=mx)))

class Xeger(object):
    """
    Does not support assertions, flags, or conditionals
    """
    def __init__(self, limit=10):
        super(Xeger, self).__init__()

        # _limit gives the largest repeat value
        self._limit = limit
        # _max is the local machine default maximum value for repeats
        self._max = re.sre_parse.parse('.*')[0][1][1]
        # _cache is used to store group references for later use
        self._cache = dict()

        # Categories of characters
        self._categories = {
            "category_any": string.printable.replace('\n', ''),
            "category_digit": string.digits,
            "category_not_digit": string.ascii_letters + string.punctuation,
            "category_space": string.whitespace,
            "category_not_space": string.whitespace,
            "category_word": string.ascii_letters + string.digits + '_',
            "category_not_word": ''.join(
                set(string.printable).difference(
                    string.ascii_letters + string.digits + '_')),
        }

        # Lookup table to implement SRE Tokens
        self._cases = {
            # These return a strategy producing strings
            "at": lambda x: st.just(''),
            "assert_not": lambda x: st.just(''),
            "literal": lambda x: st.just(unichr(x)),
            "not_literal": lambda x: from_string(
                string.printable.replace(unichr(x), '')),
            "any": lambda x: from_string(self._categories["category_any"]),
            "assert": lambda x: self._build(x[1]),
            'branch': lambda x: st.one_of(self._build(sub) for sub in x[1]),

            # These call functions returning a strategy producing strings
            "in": lambda x: self._handle_in(x),
            'min_repeat': lambda x: self._handle_repeat(*x),
            'max_repeat': lambda x: self._handle_repeat(*x),
            "subpattern": lambda x: self._handle_group(x),

            # These produce data structures used to build strategies
            "range": lambda x: [unichr(i) for i in xrange(x[0], x[1] + 1)],
            'negate': lambda x: [False],
            "category": lambda x: self._categories[str(x).lower()],

            # Locates cached group strategy producing the same strings
            "groupref": lambda x: self._cache[x],
        }

        # Lookup table of errors for unsupported SRE tokens
        self._errors = {
            'groupref_exists': "Conditionals not supported",
        }

        # These OPCODES are in sre_constants.OPCODES but not implemented here.
        # Don't know what they do, but the previous projects don't implement.
        # (Passed tests. Don't care. LOL)
        # 'min_until', 'info', 'groupref_ignore', 'repeat', 'groupref_exists',
        # 'success', 'charset', 'bigcharset', 'min_repeat_one', 'max_until',
        # 'mark', 'jump', 'failure', 'call', 'repeat_one', 'literal_ignore',
        # 'any_all', 'not_literal_ignore', 'in_ignore'

    def xeger(self, string_or_regex):
        # Initial entry method. _build_strategy is called from here
        try:
            pattern = string_or_regex.pattern
        except AttributeError:
            pattern = string_or_regex

        result = self._build(re.sre_parse.parse(pattern))
        self._cache.clear()
        return result

    def _build(self, parsed):
        # A regex is the sum of its parts (states), joined as a string
        return join([self._handle_state(state) for state in parsed])

    def _handle_state(self, state):
        # Each state is handled separately, using _cases above
        opcode, value = state
        try:
            return self._cases[str(opcode).lower()](value)
        except KeyError as e:
            # Only certain opcodes are supported. Others throw errors
            if e.args[0] in self._errors:
                raise NotImplementedError(self._errors[e.args[0]])

            raise NotImplementedError("SRE Token not implemented:", e.args[0])

    def _handle_in(self, value):
        # Handles a regex requiring one character from a group of candidates
        negated = str(value[0][0]).lower() == 'negate'
        if negated:
            # 'negated' as first token indicates a negated list of candidates
            value = value[1:]

        # Strategy candidates (e.g. literals) converted to strings with example
        candidates = (self._handle_state(i) for i in value)
        candidates = (c if isinstance(c, (basestring, list)) else c.example()
                      for c in candidates)
        candidates = list(chain(*candidates))

        if negated:
            # Negated candidates (e.g. [^abc])
            candidates = list(set(string.printable).difference(candidates))

        return st.sampled_from(candidates)

    def _handle_repeat(self, start_range, end_range, value):
        # Handles a regex with a required range of repeats
        if end_range == self._max:
            # Unlike other implementations, a *specified* max may exceed _limit
            end_range = self._limit
        return repeat(self._build(value), start_range, end_range)

    def _handle_group(self, value):
        # Groups return the same value throughout and are stored
        result = st.shared(self._build(value[1]))
        if value[0]:
            self._cache[value[0]] = result
        return result
