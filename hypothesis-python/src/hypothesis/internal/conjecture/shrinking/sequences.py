from hypothesis.internal.conjecture.shrinking.common import find_integer, \
    sort_key
from hypothesis.internal.compat import hbytes


class SequenceShrinker(object):
    def __init__(self, initial, predicate, random, full):
        self.current = tuple(initial)
        self.__full = full
        self.__predicate = predicate
        self.__random = random
        self.__change_count = 0
        self.__seen = set()

    def incorporate(self, value):
        if len(value) > len(self.current):
            return False
        key = tuple(value)
        if key in self.__seen:
            return False
        self.__seen.add(key)
        if self.__predicate(value):
            self.__change_count += 1
            self.current = key
            return True
        return False

    def consider(self, value):
        return value == self.current or self.incorporate(value)

    def run(self):
        prev = - 1
        while self.__change_count != prev:
            prev = self.__change_count
            self.delete_regions()
            if not self.__full:
                break

    def forward_gap_sweep(self):
        i = 0
        while i + 2 < len(self.current):
            attempt = list(self.current)
            del attempt[i + 2]
            del attempt[i]
            if not self.incorporate(attempt):
                i += 1
            else:
                print("DELETED GAP", i, i + 2)

    def swap(self, i, j):
        attempt = list(self.current)
        attempt[i], attempt[j] = attempt[j], attempt[i]
        if self.incorporate(attempt):
            print("SWAPPED", i, j)
            return True
        return False

    def push_back(self, i):
        if i <= 0:
            return False
        base = self.current
        def try_pushing(k):
            if k >= i:
                return False
            attempt = list(base)
            attempt[i], attempt[i - k] = attempt[i - k], attempt[i]
            return self.incorporate(attempt)
        n = find_integer(try_pushing)
        if n > 0:
            print("PUSHED FROM %d to %d" % (i, i -n))
        return n

    def delete_regions(self):
        j = 0
        while j < len(self.current):
            i = len(self.current) - 1 - j 
            start = self.current
            n = find_integer(
                lambda k: k <= i and self.consider(
                    start[:i + 1 - k] + start[i + 1:]
                )
            )
            if n > 0:
                print("DELETED %d at %d from %d. Now %d." % (
                    n, i, len(start), len(self.current) 
                ))
            j += 1


def shrink_sequence(ls, f, random, full=False):
    if len(ls) <= 1:
        return ls
    s = SequenceShrinker(ls, f, random, full)
    s.run()
    return s.current
