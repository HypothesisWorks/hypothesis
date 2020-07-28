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

import threading
from collections import deque
from math import inf

from hypothesis.internal.reflection import proxies


class DFA:
    """Base class for implementations of deterministic finite
    automata.

    This is abstract to allow for the possibility of states
    being calculated lazily as we traverse the DFA (which
    we make heavy use of in our L* implementation - see
    lstar.py for details).

    States can be of any hashable type.
    """

    def __init__(self):
        self.__caches = threading.local()

    def cached(fn):
        @proxies(fn)
        def wrapped(self, *args):
            try:
                cache = getattr(self.__caches, fn.__name__)
            except AttributeError:
                cache = {}
                setattr(self.__caches, fn.__name__, cache)

            try:
                return cache[args]
            except KeyError:
                return cache.setdefault(args, fn(self, *args))

        return wrapped

    @property
    def start(self):
        """Returns the starting state."""
        raise NotImplementedError()

    def is_accepting(self, i):
        """Returns if state ``i`` is an accepting one."""
        raise NotImplementedError()

    def transition(self, i, c):
        """Returns the state that i transitions to on reading
        character c from a string."""
        raise NotImplementedError()

    @property
    def alphabet(self):
        return range(256)

    def transitions(self, i):
        """Iterates over all pairs (byte, state) of transitions
        which do not lead to dead states."""
        for c, j in self.__raw_transitions(i):
            if not self.is_dead(j):
                yield c, j

    def matches(self, s):
        """Returns whether the string ``s`` is accepted
        by this automaton."""
        i = self.start
        for c in s:
            i = self.transition(i, c)
        return self.is_accepting(i)

    @cached
    def max_length(self, i):
        """Returns the maximum length of a string that is
        accepted when starting from i."""
        if self.is_dead(i):
            return 0
        if i in self.reachable(i):
            return inf
        next_states = {self.max_length(j) for _, j in self.transitions(i)}
        if next_states:
            return 1 + max(next_states)
        else:
            assert self.is_accepting(i)
            return 0

    @cached
    def count_strings(self, i, k):
        """Returns the number of strings of length ``k``
        that are accepted when starting from state ``i``."""
        assert k >= 0
        if k == 0:
            if self.is_accepting(i):
                return 1
            else:
                return 0
        if k > self.max_length(i):
            return 0
        return sum(self.count_strings(j, k - 1) for _, j in self.transitions(i))

    @cached
    def reachable(self, i):
        """Returns the set of all states reachable
        by traversing some non-empty string starting from
        state i."""
        reached = set()

        queue = deque([i])

        while queue:
            j = queue.popleft()
            for _, k in self.__raw_transitions(j):
                if k not in reached:
                    reached.add(k)
                    if k != i:
                        queue.append(k)
        return frozenset(reached)

    @cached
    def is_dead(self, i):
        """Returns True if no strings can be accepted
        when starting from state ``i``."""
        if self.is_accepting(i):
            return False

        return not any(self.is_accepting(j) for j in self.reachable(i))

    def all_matching_strings_of_length(self, k):
        """Yields all matching strings whose length is ``k``, in ascending
        lexicographic order."""
        if self.count_strings(self.start, k) == 0:
            return

        # This tracks a path through the DFA. We alternate between growing
        # it until it has length ``k`` and is in an accepting state, then
        # yielding that as a result, then modifying it so that the next
        # time we do that it will yield the lexicographically next matching
        # string.
        path = bytearray()

        # Tracks the states that are visited by following ``path`` from the
        # starting point.
        states = [self.start]

        while True:
            # First we build up our current best prefix to the lexicographically
            # first string starting with it.
            while len(path) < k:
                state = states[-1]
                for c, j in self.transitions(state):
                    if self.count_strings(j, k - len(path) - 1) > 0:
                        states.append(j)
                        path.append(c)
                        break
                else:  # pragma: no cover
                    assert False
            assert self.is_accepting(states[-1])
            assert len(states) == len(path) + 1
            yield bytes(path)

            # Now we want to replace this string with the prefix that will
            # cause us to extend to its lexicographic successor. This can
            # be thought of as just repeatedly moving to the next lexicographic
            # successor until we find a matching string, but we're able to
            # use our length counts to jump over long sequences where there
            # cannot be a match.
            while True:
                # As long as we are in this loop we are trying to move to
                # the successor of the current string.

                # If we've removed the entire prefix then we're done - no
                # successor is possible.
                if not path:
                    return

                if path[-1] == 255:
                    # If our last element is maximal then the we have to "carry
                    # the one" - our lexicographic successor must be incremented
                    # earlier than this.
                    path.pop()
                    states.pop()
                else:
                    # Otherwise increment by one.
                    path[-1] += 1
                    states[-1] = self.transition(states[-2], path[-1])

                    # If there are no strings of the right length starting from
                    # this prefix we need to keep going. Otherwise, this is
                    # the right place to be and we break out of our loop of
                    # trying to find the successor because it starts here.
                    if self.count_strings(states[-1], k - len(path)) > 0:
                        break

    def all_matching_strings(self):
        """Iterate over all strings matched by this automaton
        in shortlex-ascending order."""
        if self.is_accepting(self.start):
            yield b""

        # max_length might be infinite, hence the while loop
        max_length = self.max_length(self.start)
        length = 1
        while length <= max_length:
            yield from self.all_matching_strings_of_length(length)
            length += 1

    def __raw_transitions(self, i):
        for c in self.alphabet:
            j = self.transition(i, c)
            yield c, j


DEAD = "DEAD"


class ConcreteDFA(DFA):
    def __init__(self, transitions, accepting, start=0):
        super().__init__()
        self.__start = start
        self.__accepting = accepting
        self.__transitions = transitions

    def __repr__(self):
        if self.__start != 0:
            return "ConcreteDFA(%r, %r, start=%r)" % (
                self.__transitions,
                self.__accepting,
                self.__start,
            )
        else:
            return "ConcreteDFA(%r, %r)" % (self.__transitions, self.__accepting,)

    @property
    def start(self):
        return self.__start

    def is_accepting(self, i):
        return i in self.__accepting

    def transition(self, i, c):
        """Returns the state that i transitions to on reading
        character c from a string."""
        if i == DEAD:
            return i
        try:
            return self.__transitions[i][c]
        except KeyError:
            return DEAD
