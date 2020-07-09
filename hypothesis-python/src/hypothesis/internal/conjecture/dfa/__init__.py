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

    def is_dead(self, i):
        """Returns True if no strings can be accepted
        when starting from state ``i``."""
        if self.is_accepting(i):
            return False

        try:
            cache = self.__caches.dead
        except AttributeError:
            cache = {}
            self.__caches.dead = cache

        try:
            return cache[i]
        except KeyError:
            pass
        seen = set()
        pending = deque([i])
        result = True
        while pending:
            j = pending.popleft()
            if j in seen:
                continue
            seen.add(j)
            if self.is_accepting(j):
                result = False
                break
            else:
                for _, k in self.__raw_transitions(j):
                    pending.append(k)
        if result:
            for j in seen:
                cache[j] = True
        else:
            cache[i] = False
        return result

    def all_matching_strings(self):
        """Iterate over all strings matched by this automaton
        in shortlex-ascending order."""
        queue = deque([(self.start, b"")])
        while queue:
            i, path = queue.popleft()
            if self.is_accepting(i):
                yield path
            for c, j in self.transitions(i):
                queue.append((j, path + bytes([c])))

    def __raw_transitions(self, i):
        for c in range(256):
            j = self.transition(i, c)
            yield c, j
