from hypothesis.internal.conjecture.shrinking.common import find_integer


class SequenceShrinker(object):
    def __init__(self, initial, predicate, random):
        self.current = tuple(initial)
        self.bench = hbytes().join(initial)
        self.__predicate = predicate
        self.__random = random

    def incorporate(self, value):
        if hbytes().join(value) >= bench:
            return False
        if self.__predicate(value):
            self.current = tuple(value)
            self.bench = hbytes().join(self.current)
            return True
        return False

    def run(self):
        i = 1
        while i < len(self.current):
            j = i
            while j > 0:
                attempt = list(self.current)
                attempt[j - 1], attempt[j] = attempt[j], attempt[j - 1]
                if not self.incorporate(attempt):
                    break


def shrink_sequence(ls, f, random):
    if len(ls) <= 1:
        return ls
    s = SequenceShrinker(ls, f, random)
    s.run()
    return s.current
