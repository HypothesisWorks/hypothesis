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

"""A module for miscellaneous useful bits and bobs that don't
obviously belong anywhere else. If you spot a better home for
anything that lives here, please move it."""

import array
import sys


def array_or_list(code, contents):
    if code == "O":
        return list(contents)
    return array.array(code, contents)


def replace_all(buffer, replacements):
    """Substitute multiple replacement values into a buffer.

    Replacements is a list of (start, end, value) triples.
    """

    result = bytearray()
    prev = 0
    offset = 0
    for u, v, r in replacements:
        result.extend(buffer[prev:u])
        result.extend(r)
        prev = v
        offset += len(r) - (v - u)
    result.extend(buffer[prev:])
    assert len(result) == len(buffer) + offset
    return bytes(result)


ARRAY_CODES = ["B", "H", "I", "L", "Q", "O"]
NEXT_ARRAY_CODE = dict(zip(ARRAY_CODES, ARRAY_CODES[1:]))


class IntList:
    """Class for storing a list of non-negative integers compactly.

    We store them as the smallest size integer array we can get
    away with. When we try to add an integer that is too large,
    we upgrade the array to the smallest word size needed to store
    the new value."""

    __slots__ = ("__underlying",)

    def __init__(self, values=()):
        for code in ARRAY_CODES:
            try:
                self.__underlying = array_or_list(code, values)
                break
            except OverflowError:
                pass
        else:  # pragma: no cover
            raise AssertionError("Could not create storage for %r" % (values,))
        if isinstance(self.__underlying, list):
            for v in self.__underlying:
                if v < 0 or not isinstance(v, int):
                    raise ValueError("Could not create IntList for %r" % (values,))

    @classmethod
    def of_length(self, n):
        return IntList(array_or_list("B", [0]) * n)

    def count(self, n):
        return self.__underlying.count(n)

    def __repr__(self):
        return "IntList(%r)" % (list(self),)

    def __len__(self):
        return len(self.__underlying)

    def __getitem__(self, i):
        if isinstance(i, slice):
            return IntList(self.__underlying[i])
        return self.__underlying[i]

    def __delitem__(self, i):
        del self.__underlying[i]

    def insert(self, i, v):
        self.__underlying.insert(i, v)

    def __iter__(self):
        return iter(self.__underlying)

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, IntList):
            return NotImplemented
        return self.__underlying == other.__underlying

    def __ne__(self, other):
        if self is other:
            return False
        if not isinstance(other, IntList):
            return NotImplemented
        return self.__underlying != other.__underlying

    def append(self, n):
        i = len(self)
        self.__underlying.append(0)
        self[i] = n

    def __setitem__(self, i, n):
        while True:
            try:
                self.__underlying[i] = n
                return
            except OverflowError:
                assert n > 0
                self.__upgrade()

    def extend(self, ls):
        for n in ls:
            self.append(n)

    def __upgrade(self):
        code = NEXT_ARRAY_CODE[self.__underlying.typecode]
        self.__underlying = array_or_list(code, self.__underlying)


def binary_search(lo, hi, f):
    """Binary searches in [lo , hi) to find
    n such that f(n) == f(lo) but f(n + 1) != f(lo).
    It is implicitly assumed and will not be checked
    that f(hi) != f(lo).
    """

    reference = f(lo)

    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if f(mid) == reference:
            lo = mid
        else:
            hi = mid
    return lo


def uniform(random, n):
    """Returns a bytestring of length n, distributed uniformly at random."""
    return random.getrandbits(n * 8).to_bytes(n, "big")


class LazySequenceCopy:
    """A "copy" of a sequence that works by inserting a mask in front
    of the underlying sequence, so that you can mutate it without changing
    the underlying sequence. Effectively behaves as if you could do list(x)
    in O(1) time. The full list API is not supported yet but there's no reason
    in principle it couldn't be."""

    def __init__(self, values):
        self.__values = values
        self.__len = len(values)
        self.__mask = None

    def __len__(self):
        return self.__len

    def pop(self):
        if len(self) == 0:
            raise IndexError("Cannot pop from empty list")
        result = self[-1]
        self.__len -= 1
        if self.__mask is not None:
            self.__mask.pop(self.__len, None)
        return result

    def __getitem__(self, i):
        i = self.__check_index(i)
        default = self.__values[i]
        if self.__mask is None:
            return default
        else:
            return self.__mask.get(i, default)

    def __setitem__(self, i, v):
        i = self.__check_index(i)
        if self.__mask is None:
            self.__mask = {}
        self.__mask[i] = v

    def __check_index(self, i):
        n = len(self)
        if i < -n or i >= n:
            raise IndexError("Index %d out of range [0, %d)" % (i, n))
        if i < 0:
            i += n
        assert 0 <= i < n
        return i


def clamp(lower, value, upper):
    """Given a value and lower/upper bounds, 'clamp' the value so that
    it satisfies lower <= value <= upper."""
    return max(lower, min(value, upper))


def swap(ls, i, j):
    """Swap the elements ls[i], ls[j]."""
    if i == j:
        return
    ls[i], ls[j] = ls[j], ls[i]


def stack_depth_of_caller():
    """Get stack size for caller's frame.

    From https://stackoverflow.com/a/47956089/9297601 , this is a simple
    but much faster alternative to `len(inspect.stack(0))`.  We use it
    with get/set recursionlimit to make stack overflows non-flaky; see
    https://github.com/HypothesisWorks/hypothesis/issues/2494 for details.
    """
    frame = sys._getframe(2)
    size = 1
    while frame:
        frame = frame.f_back
        size += 1
    return size


def find_integer(f):
    """Finds a (hopefully large) integer such that f(n) is True and f(n + 1) is
    False.

    f(0) is assumed to be True and will not be checked.
    """
    # We first do a linear scan over the small numbers and only start to do
    # anything intelligent if f(4) is true. This is because it's very hard to
    # win big when the result is small. If the result is 0 and we try 2 first
    # then we've done twice as much work as we needed to!
    for i in range(1, 5):
        if not f(i):
            return i - 1

    # We now know that f(4) is true. We want to find some number for which
    # f(n) is *not* true.
    # lo is the largest number for which we know that f(lo) is true.
    lo = 4

    # Exponential probe upwards until we find some value hi such that f(hi)
    # is not true. Subsequently we maintain the invariant that hi is the
    # smallest number for which we know that f(hi) is not true.
    hi = 5
    while f(hi):
        lo = hi
        hi *= 2

    # Now binary search until lo + 1 = hi. At that point we have f(lo) and not
    # f(lo + 1), as desired..
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if f(mid):
            lo = mid
        else:
            hi = mid
    return lo


def pop_random(random, seq):
    """Remove and return a random element of seq. This runs in O(1) but leaves
    the sequence in an arbitrary order."""
    i = random.randrange(0, len(seq))
    swap(seq, i, len(seq) - 1)
    return seq.pop()
