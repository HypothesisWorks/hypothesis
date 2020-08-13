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
from collections import defaultdict, deque
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

    def all_matching_regions(self, string):
        """Return all pairs ``(u, v)`` such that ``self.matches(string[u:v])``."""

        # Stack format: (k, state, indices). After reading ``k`` characters
        # starting from any i in ``indices`` the DFA would be at ``state``.
        stack = [(0, self.start, range(len(string)))]

        results = []

        while stack:
            k, state, indices = stack.pop()

            # If the state is dead, abort early - no point continuing on
            # from here where there will be no more matches.
            if self.is_dead(state):
                continue

            # If the state is accepting, then every one of these indices
            # has a matching region of length ``k`` starting from it.
            if self.is_accepting(state):
                results.extend([(i, i + k) for i in indices])

            next_by_state = defaultdict(list)

            for i in indices:
                if i + k < len(string):
                    c = string[i + k]
                    next_by_state[self.transition(state, c)].append(i)
            for next_state, next_indices in next_by_state.items():
                stack.append((k + 1, next_state, next_indices))
        return results

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
        if k == 0:
            if self.is_accepting(self.start):
                yield b""
            return

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

    def all_matching_strings(self, min_length=0):
        """Iterate over all strings matched by this automaton
        in shortlex-ascending order."""
        # max_length might be infinite, hence the while loop
        max_length = self.max_length(self.start)
        length = min_length
        while length <= max_length:
            yield from self.all_matching_strings_of_length(length)
            length += 1

    def __raw_transitions(self, i):
        for c in self.alphabet:
            j = self.transition(i, c)
            yield c, j

    def canonicalise(self):
        """Return a canonical version of ``self`` as a ConcreteDFA.

        The DFA is not minimized, but nodes are sorted and relabelled
        and dead nodes are pruned, so two minimized DFAs for the same
        language will end up with identical canonical representatives.
        This is mildly important because it means that the output of
        L* should produce the same canonical DFA regardless of what
        order we happen to have run it in.
        """
        # We map all states to their index of appearance in depth
        # first search. This both is useful for canonicalising and
        # also allows for states that aren't integers.
        state_map = {}
        reverse_state_map = []
        accepting = set()

        seen = set()

        queue = deque([self.start])
        while queue:
            state = queue.popleft()
            if state in state_map:
                continue
            i = len(reverse_state_map)
            if self.is_accepting(state):
                accepting.add(i)
            reverse_state_map.append(state)
            state_map[state] = i
            for _, j in self.transitions(state):
                if j in seen:
                    continue
                seen.add(j)
                queue.append(j)

        transitions = [
            {c: state_map[s] for c, s in self.transitions(t)} for t in reverse_state_map
        ]

        result = ConcreteDFA(transitions, accepting)
        assert self.equivalent(result)
        return result

    def equivalent(self, other):
        """Checks whether this DFA and other match precisely the same
        language.

        Uses the classic algorith of Hopcroft and Karp (more or less):
        Hopcroft, John E. A linear algorithm for testing equivalence
        of finite automata. Vol. 114. Defense Technical Information Center, 1971.
        """

        # The basic idea of this algorithm is that we repeatedly
        # merge states that would be equivalent if the two start
        # states were. This starts by merging the two start states,
        # and whenever we merge two states merging all pairs of
        # states that are reachable by following the same character
        # from that point.
        #
        # Whenever we merge two states, we check if one of them
        # is accepting and the other non-accepting. If so, we have
        # obtained a contradiction and have made a bad merge, so
        # the two start states must not have been equivalent in the
        # first place and we return False.
        #
        # If the languages matched are different then some string
        # is contained in one but not the other. By looking at
        # the pairs of states visited by traversing the string in
        # each automaton in parallel, we eventually come to a pair
        # of states that would have to be merged by this algorithm
        # where one is accepting and the other is not. Thus this
        # algorithm always returns False as a result of a bad merge
        # if the two languages are not the same.
        #
        # If we successfully complete all merges without a contradiction
        # we can thus safely return True.

        # We maintain a union/find table for tracking merges of states.
        table = {}

        def find(s):
            trail = [s]
            while trail[-1] in table and table[trail[-1]] != trail[-1]:
                trail.append(table[trail[-1]])

            for t in trail:
                table[t] = trail[-1]

            return trail[-1]

        def union(s, t):
            s = find(s)
            t = find(t)
            table[s] = t

        alphabet = sorted(set(self.alphabet) | set(other.alphabet))

        queue = deque([((self.start, other.start))])
        while queue:
            self_state, other_state = queue.popleft()

            # We use a DFA/state pair for keys because the same value
            # may represent a different state in each DFA.
            self_key = (self, self_state)
            other_key = (other, other_state)

            # We have already merged these, no need to remerge.
            if find(self_key) == find(other_key):
                continue

            # We have found a contradiction, therefore the two DFAs must
            # not be equivalent.
            if self.is_accepting(self_state) != other.is_accepting(other_state):
                return False

            # Merge the two states
            union(self_key, other_key)

            # And also queue any logical consequences of merging those
            # two states for merging.
            for c in alphabet:
                queue.append(
                    (self.transition(self_state, c), other.transition(other_state, c))
                )
        return True


DEAD = "DEAD"


class ConcreteDFA(DFA):
    """A concrete representation of a DFA in terms of an explicit list
    of states."""

    def __init__(self, transitions, accepting, start=0):
        """
        * ``transitions`` is a list where transitions[i] represents the
          valid transitions out of state ``i``. Elements may be either dicts
          (in which case they map characters to other states) or lists. If they
          are a list they may contain tuples of length 2 or 3. A tuple ``(c, j)``
          indicates that this state transitions to state ``j`` given ``c``. A
          tuple ``(u, v, j)`` indicates this state transitiosn to state ``j``
          given any ``c`` with ``u <= c <= v``.
        * ``accepting`` is a set containing the integer labels of accepting
          states.
        * ``start`` is the integer label of the starting state.
        """
        super().__init__()
        self.__start = start
        self.__accepting = accepting
        self.__transitions = list(transitions)

    def __repr__(self):
        transitions = []
        # Particularly for including in source code it's nice to have the more
        # compact repr, so where possible we convert to the tuple based representation
        # which can represent ranges more compactly.
        for i in range(len(self.__transitions)):
            table = []
            for c, j in self.transitions(i):
                if not table or j != table[-1][-1] or c != table[-1][1] + 1:
                    table.append([c, c, j])
                else:
                    table[-1][1] = c
            transitions.append([(u, j) if u == v else (u, v, j) for u, v, j in table])

        if self.__start != 0:
            return "ConcreteDFA(%r, %r, start=%r)" % (
                transitions,
                self.__accepting,
                self.__start,
            )
        else:
            return "ConcreteDFA(%r, %r)" % (transitions, self.__accepting,)

    @property
    def start(self):
        return self.__start

    def is_accepting(self, i):
        return i in self.__accepting

    def transition(self, state, char):
        """Returns the state that i transitions to on reading
        character c from a string."""
        if state == DEAD:
            return DEAD

        table = self.__transitions[state]

        # Given long transition tables we convert them to
        # dictionaries for more efficient lookup.
        if not isinstance(table, dict) and len(table) >= 5:
            new_table = {}
            for t in table:
                if len(t) == 2:
                    new_table[t[0]] = t[1]
                else:
                    u, v, j = t
                    for c in range(u, v + 1):
                        new_table[c] = j
            self.__transitions[state] = new_table
            table = new_table

        if isinstance(table, dict):
            try:
                return self.__transitions[state][char]
            except KeyError:
                return DEAD
        else:
            for t in table:
                if len(t) == 2:
                    if t[0] == char:
                        return t[1]
                else:
                    u, v, j = t
                    if u <= char <= v:
                        return j
            return DEAD
