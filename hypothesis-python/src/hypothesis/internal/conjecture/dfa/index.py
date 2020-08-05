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

from hypothesis.internal.conjecture.junkdrawer import find_integer


class DFAIndex:
    """Represents the language matched by some DFA as a random
    access collection sorted in shortlex order."""

    def __init__(self, dfa):
        self.dfa = dfa

        self.__length = None
        self.__max_string_length = self.dfa.max_length(self.dfa.start)
        self.__running_counts = [self.dfa.count_strings(self.dfa.start, 0)]

    def __count_strings_up_to(self, length):
        length = min(length, self.dfa.max_length(self.dfa.start))
        while length >= len(self.__running_counts):
            self.__running_counts.append(
                self.dfa.count_strings(self.dfa.start, len(self.__running_counts))
                + self.__running_counts[-1]
            )
        return self.__running_counts[length]

    def __iter__(self):
        return self.dfa.all_matching_strings()

    def length(self):
        """Like len(self) but will return math.inf when the collection
        is infinite rather than raising an error."""
        max_length = self.__max_string_length
        if self.__length is None:
            if not math.isfinite(max_length):
                self.__length = math.inf
            else:
                self.__length = self.__count_strings_up_to(max_length)
        return self.__length

    def __len__(self):
        return self.length()

    def __getitem__(self, i):
        if i < 0:
            raise IndexError("Negative indices not supported")

        if i == 0 and self.dfa.matches(b""):
            return b""

        length = (
            find_integer(
                lambda n: n <= self.__max_string_length
                and self.__count_strings_up_to(n) <= i
            )
            + 1
        )
        if length > self.__max_string_length:
            assert i >= self.length()
            raise IndexError("%d out of range [0, %d)" % (i, len(self)))

        running_index = i - self.__count_strings_up_to(length - 1)

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

        result = self.__count_strings_up_to(len(string) - 1)

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
