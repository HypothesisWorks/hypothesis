from hypothesis.internal.conjecture.dfa import DFA
from collections import deque


class ExperimentDFA(DFA):
    def __init__(self, member, experiments):
        self.__experiments = tuple(experiments)
        self.__member = member

        self.__states = [b'']
        self.__rows_to_states = {tuple(map(member, experiments)): 0}
        self.__transition_cache = {}

    def label(self, i):
        return self.__states[i]

    @property
    def start(self):
        return 0

    def is_accepting(self, i):
        return self.__member(self.__states[i])

    def transition(self, i, c):
        key = (i, c)
        try:
            return self.__transition_cache[key]
        except KeyError:
            pass
        s = self.__states[i]
        t = s + bytes([c])
        row = tuple(self.__member(t + e) for e in self.__experiments)
        try:
            result = self.__rows_to_states[row]
        except KeyError:
            result = len(self.__states)
            self.__states.append(t)
            self.__rows_to_states[row] = result
        self.__transition_cache[key] = result
        return result


class LStar(object):
    def __init__(self, member):
        self.__experiments = []
        self.__cache = {}
        self.__member = member

        self.__add_experiment(b'')

    def member(self, s):
        s = bytes(s)
        try:
            return self.__cache[s]
        except KeyError:
            return self.__cache.setdefault(s, self.__member(s))

    @property
    def generation(self):
        return len(self.__experiments)

    def __add_experiment(self, e):
        self.__experiments.append(e)
        self.__dfa = None

    @property
    def dfa(self):
        if self.__dfa is None:
            self.__dfa = ExperimentDFA(self.member, self.__experiments)
        return self.__dfa

    def repair(self, s):
        correct_outcome = self.member(s)

        while True:
            dfa = self.dfa
            state = dfa.start

            for i, c in enumerate(s):
                rest = s[i:]
                if self.member(dfa.label(state) + rest) != correct_outcome:
                    self.__add_experiment(rest)
                    break
                state = dfa.transition(state, c)
            else:
                assert dfa.is_accepting(state) == correct_outcome
                break

    def dead(self, i):
        return not (
            self.accepting(i) or
            any(self.accepting(j) for j in self.reachable(i))
        )

    def __paths_from(self, i):
        visited = set()
        queue = deque([(i, b'')])
        broken = False
        while queue and not broken:
            j, path = queue.popleft()
            for c in range(256):
                k = self.transition(j, c)
                if k in visited:
                    continue
                visited.add(k)
                new_path = path + bytes([c]) 
                yield k, new_path
                queue.append((k, new_path))

    def __complete(self, i):
        assert not self.dead(i)
        for j, path in self.__paths_from(i):
            if self.accepting(j):
                return path

    def find_minimal(self):
        assert not self.dead(self.start)
        while True:
            visited = set()
            queue = deque([(self.start, b'')])
            broken = False
            while queue and not broken:
                i, path = queue.popleft()
                assert not self.accepting(i)
                for c in range(256):
                    j = self.transition(i, c)
                    if j in visited:
                        continue
                    visited.add(j)
                    t = path + bytes([c])
                    if self.accepting(j):
                        if self.member(t):
                            return t
                        else:
                            self.repair(t)
                            broken = True
                            break
                    else:
                        if self.dead(j):
                            continue
                        else:
                            queue.append((j, t))

    def reachable(self, i):
        try:
            return self.__reachable[i]
        except KeyError:
            pass
        reached = set()
        visited = set()
        queue = deque([i])
        result = True
        while queue:
            j = queue.popleft()
            if j in visited:
                continue
            visited.add(j)
            for c in range(256):
                k = self.transition(j, c)
                if k not in reached:
                    reached.add(k)
                    queue.append(k)
        self.__reachable[i] = reached
        return reached
