# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import inspect
from random import Random
from itertools import islice

from hypothesis.errors import InvalidArgument


class RandomWithSeed(Random):

    """A subclass of Random designed to expose the seed it was initially
    provided with.

    We consistently use this instead of Random objects because it makes
    examples much easier to recreate.

    """

    def __init__(self, seed):
        super(RandomWithSeed, self).__init__(seed)
        self.seed = seed

    def __repr__(self):
        return 'RandomWithSeed(%s)' % (self.seed,)


class Stream(object):

    """A stream is a possibly infinite list. You can index into it, and you can
    iterate over it, but you can't ask its length and iterating over it will
    not necessarily terminate.

    Behind the scenes streams are backed by a generator, but they "remember"
    the values as they evaluate them so you can replay them later.

    Internally Hypothesis uses the fact that you can tell how much of a stream
    has been evaluated, but you shouldn't use that. The only public APIs of
    a Stream are that you can index, slice, and iterate it.

    """

    def __init__(self, generator=None):
        if generator is None:
            generator = iter(())
        elif not inspect.isgenerator(generator):
            generator = iter(generator)
        self.generator = generator
        self.fetched = []

    def map(self, f):
        return Stream(f(v) for v in self)

    def __iter__(self):
        i = 0
        while i < len(self.fetched):
            yield self.fetched[i]
            i += 1
        while True:
            v = next(self.generator)
            self.fetched.append(v)
            yield v

    def __getitem__(self, key):
        if isinstance(key, slice):
            return Stream(islice(
                iter(self),
                key.start, key.stop, key.step
            ))

        if not isinstance(key, int):
            raise InvalidArgument('Cannot index stream with %s' % (
                type(key).__name__,))
        self._thunk_to(key + 1)
        return self.fetched[key]

    def with_value(self, i, value):
        s = Stream(self)
        s._thunk_to(i + 1)
        s.fetched[i] = value
        return s

    def _thunk_to(self, i):
        it = iter(self)
        try:
            while len(self.fetched) < i:
                next(it)
        except StopIteration:
            raise IndexError(
                'Index %d out of bounds for finite stream of length %d' % (
                    i, len(self.fetched)
                )
            )

    def _thunked(self):
        return len(self.fetched)

    def __repr__(self):
        if not self.fetched:
            return 'Stream(...)'

        return 'Stream(%s, ...)' % (
            ', '.join(map(repr, self.fetched))
        )

    def __deepcopy__(self, table):
        return self

    def __copy__(self):
        return self
