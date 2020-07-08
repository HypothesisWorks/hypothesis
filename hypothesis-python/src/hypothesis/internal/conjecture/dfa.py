
from hypothesis.utils.conventions import UniqueIdentifier
from collections import deque
from functools import wraps



DEAD = UniqueIdentifier("DEAD")


class DFA:
    def __init__(self, data):
        """Accepts a list of pairs (accepting, transitions), where transitions is
        a list of triples (start, end, j) representing that in state i, any
        byte c in start <= c <= end will transition to state j."""
        self.__states = tuple([
            (accepting, tuple(sorted(transitions)))
            for accepting, transitions in data
        ])
        self.__minimal = None
        self.__predecessor_cache = {}
        self.__completions = [None] * len(self.__states)

    def __repr__(self):
        return "DFA(%r)" % (self.__states,)

    def __eq__(self, other):
        if isinstance(other, DFA):
            return self.__states == other.__states
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, DFA):
            return self.__states != other.__states
        else:
            return NotImplemented

    def __hash__(self):
        return hash(self.__states)

    @property
    def start(self):
        return 0

    def accepting(self, i):
        if i == DEAD:
            return False
        return self.__states[i][0]

    def transitions(self, i):
        if i == DEAD:
            return
        for start, end, state in self.__states[i][1]:
            for c in range(start, end + 1):
                yield c, state

    def dead(self, i):
        return i == DEAD

    def transition(self, i, c):
        if i == DEAD:
            return DEAD
        for start, end, j in self.__states[i][1]:
            if start <= c <= end:
                return j
        return DEAD

    def matches(self, s):
        i = self.start
        for c in s:
            i = self.transition(i, c)
        return self.accepting(i)

    def all_matches(self, s):
        results = []
        pending = [(range(len(s)), 0, self.start)]
        while pending:
            indices, length, state = pending.pop()
            indices = [i for i in indices if i + length < len(s)]

            partition = {}

            for i in indices:
                c = s[i + length]

                try:
                    new_indices = partition[c][1]
                except KeyError:
                    new_state = self.transition(state, c)
                    new_indices = []
                    partition[c] = (new_state, new_indices)
                new_indices.append(i)

                for new_state, new_indices in partition.values():
                    if self.dead(new_state):
                        continue
                    if self.accepting(new_state):
                        for i in new_indices:
                            results.append((i, i + length + 1))
                    pending.append((new_indices, length + 1, new_state))
        return results

def cached(f):
    cache_name = '__cache_%s' % (f.__name__,)

    @wraps(f)
    def accept(self, *args):
        try:
            cache = getattr(self, cache_name)
        except AttributeError:
            cache = {}
            setattr(self, cache_name, cache)
        try:
            return cache[args]
        except KeyError:
            pass
        result = f(self, *args)
        cache[args] = result
        return result
    return accept


INF = float('inf')


class Indexer(object):
    def __init__(self, dfa):
        self.__dfa = dfa
        self.__index_to_string = {}
        self.__string_to_index = {}

    def __getitem__(self, i):
        n = self.length
        if i >= n or i < 0:
            raise IndexError("Index %d out of bounds [0, %d)" % (i, n))

        length_of_string = 0
        while True:
            c = self.__count_strings(0, length_of_string)
            if c > i:
                break
            else:
                i -= c
                length_of_string += 1

        state = 0
        result = bytearray()
        while len(result) < length_of_string:
            for b, j in sorted(self.__dfa.transitions(state)):
                c = self.__count_strings(j, length_of_string - len(result) - 1)
                if c <= i:
                    i -= c
                else:
                    result.append(b)
                    state = j
                    break
        assert self.__dfa.accepting(state)
        result = bytes(result)
        self.__index_to_string[i] = result
        self.__string_to_index[result] = i
        return result

    def index(self, s):
        count = 0
        for n in range(len(s)):
            count += self.__count_strings(0, n)
        state = self.__dfa.start
        for i, c in enumerate(s):
            for b in range(c):
                new_state = self.__dfa.transition(state, b)
                count += self.__count_strings(new_state, len(s) - i - 1)
            state = self.__dfa.transition(state, c)
        self.__index_to_string[count] = s
        self.__string_to_index[s] = count
        return count

    def __len__(self):
        result = self.length
        if result == INF:
            raise ValueError("Infinite sequence")
        return result

    @property
    @cached
    def length(self):
        n = self.__max_length(self.__dfa.start)
        if n == INF:
            return INF
        else:
            return sum([
                self.__count_strings(self.__dfa.start, k)
                for k in range(n + 1)
            ])

    @cached
    def __max_length(self, i):
        if self.__is_unbounded(i):
            return float('inf')
        elif self.__is_dead(i):
            return 0
        else:
            dests = {j for _, j in self.__dfa.transitions(i)}
            if dests:
                return 1 + max([
                    self.__max_length(j)
                    for j in dests
                ])
            else:
                return 0

    @cached
    def __is_dead(self, i):
        if self.__dfa.accepting(i):
            return False
        return not any(self.__dfa.accepting(j) for j in self.__reachable(i))

    @cached
    def __reachable(self, i):
        queue = deque([i])
        seen = set()
        reached = set()
        while queue:
            j = queue.popleft()
            if j in seen:
                continue
            seen.add(j)
            for _, k in self.__dfa.transitions(j):
                reached.add(k)
                if k not in seen:
                    queue.append(k)
        return frozenset(reached)

    @cached
    def __is_unbounded(self, i):
        if self.__is_dead(i):
            return False
        if i in self.__reachable(i):
            return True
        for j in self.__reachable(i):
            if not self.__is_dead(j) and j in self.__reachable(j):
                return True
        return False

    @cached
    def __count_strings(self, i, k):
        assert k >= 0
        if self.__is_dead(i):
            return 0
        if k == 0:
            if self.__dfa.accepting(i):
                return 1
            else:
                return 0
        else:
            return sum([
                self.__count_strings(j, k - 1)
                for (_, j) in self.__dfa.transitions(i)
            ])

    def __iter__(self):
        queue = deque([(self.__dfa.start, b'')])
        while queue:
            i, path = queue.popleft()
            if self.__is_dead(i):
                continue
            if self.__dfa.accepting(i):
                yield path
            for c, j in self.__dfa.transitions(i):
                queue.append((j, path + bytes([c])))
