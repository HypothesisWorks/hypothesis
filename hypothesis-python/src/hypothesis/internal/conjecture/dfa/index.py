# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

import math


class DFAIndex:
    """Represents the language matched by some DFA as a random
    access collection sorted in shortlex order."""

    def __init__(self, dfa):
        self.dfa = dfa

        self.__length = None

    def __iter__(self):
        return self.dfa.all_matching_strings()

    def length(self):
        """Like len(self) but will return math.inf when the collection
        is infinite rather than raising an error."""
        if self.__length is None:
            if not math.isfinite(self.dfa.max_length(self.dfa.start)):
                self.__length = math.inf
            else:
                self.__length = sum(
                    self.dfa.count_strings(self.dfa.start, k)
                    for k in range(self.dfa.max_length(self.dfa.start) + 1)
                )
        return self.__length

    def __len__(self):
        return self.length()

    def __getitem__(self, i):
        if i < 0:
            raise IndexError("Negative indices not supported")

        running_index = i

        length = 0
        while True:
            n = self.dfa.count_strings(self.dfa.start, length)
            if n > running_index:
                break
            running_index -= n
            length += 1
            if length > self.dfa.max_length(self.dfa.start):
                assert i >= self.length()
                raise IndexError("Index %d out of range [0, %d)" % (i, self.length()))

        result = bytearray()
        state = self.dfa.start
        while len(result) < length:
            for c, next_state in self.dfa.transitions(state):
                n_to_skip = self.dfa.count_strings(next_state, length - len(result) - 1)
                if running_index < n_to_skip:
                    result.append(c)
                    state = next_state
                    break
                else:
                    running_index -= n_to_skip
            else:  # pragma: no cover
                assert False, "Count mismatch"
        assert len(result) == length
        return bytes(result)

    def index(self, string):
        """Return the index of string in this collection, so that
        self[self.index(string)] == string. Raises ValueError if
        string is not in this collection."""

        if not self.dfa.matches(string):
            raise ValueError("%r not in language" % (string,))

        if not string:
            return 0

        result = 0
        for k in range(len(string)):
            result += self.dfa.count_strings(self.dfa.start, k)

        state = self.dfa.start
        for i, c in enumerate(string):
            remainder = len(string) - i - 1
            assert remainder >= 0
            for d in range(c):
                result += self.dfa.count_strings(
                    self.dfa.transition(state, d), remainder
                )
            state = self.dfa.transition(state, c)
        return result
