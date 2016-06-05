from __future__ import division, print_function, absolute_import


class AliasChooser(object):

    def __init__(self, weights):
        assert len(weights) >= 2
        weights = list(weights)
        total = sum(weights)
        n = len(weights)
        multiplier = n // gcd(total, n)
        for i in range(n):
            weights[i] *= multiplier
        total = sum(weights)
        assert total % n == 0
        capacity = total // n
        aliases = [None] * n
        indices = sorted(range(n), key=weights.__getitem__, reverse=True)
        i = 0
        while i < len(indices):
            overfull = indices[i]
            if weights[overfull] == capacity:
                i += 1
            else:
                assert i + 1 < len(indices)
                underfull = indices.pop()
                assert weights[overfull] > capacity
                assert weights[underfull] < capacity
                aliases[underfull] = overfull
                weights[overfull] -= (capacity - weights[underfull])
                if weights[overfull] < capacity:
                    assert i + 1 < len(indices)
                    for j in range(i, len(indices) - 1):
                        indices[j] = indices[j + 1]
                    indices[-1] = overfull
        self.size = len(weights)
        self.total = total
        self.capacity = capacity
        self.weights = weights
        self.aliases = aliases
        for w in weights:
            assert 0 <= w <= capacity
        assert len(weights) == len(aliases)

    def choose(self, random):
        n = len(self.weights)
        probe = random.randint(0, self.total - 1)
        i = probe % n
        r = (probe // n + 1)
        assert 1 <= r <= self.capacity
        assert 0 <= i < n
        if r <= self.weights[i]:
            return i
        else:
            r = self.aliases[i]
            assert r is not None
            return r


def gcd(a, b):
    while b != 0:
        t = b
        b = a % b
        a = t
    return a
