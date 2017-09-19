# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import attr


@attr.s(slots=True)
class Entry(object):
    key = attr.ib()
    value = attr.ib()
    score = attr.ib()


class GenericCache(object):
    __slots__ = ('keys_to_indices', 'data', 'max_size')

    def __init__(self, max_size):
        self.keys_to_indices = {}
        self.data = []
        self.max_size = max_size

    def __len__(self):
        assert len(self.keys_to_indices) == len(self.data)
        return len(self.data)

    def __getitem__(self, key):
        i = self.keys_to_indices[key]
        result = self.data[i]
        self.on_access(result.key, result.value, result.score)
        self.__balance(i)
        return result.value

    def __setitem__(self, key, value):
        if self.max_size == 0:
            return
        evicted = None
        try:
            i = self.keys_to_indices[key]
        except KeyError:
            entry = Entry(key, value, self.new_entry(key, value))
            if len(self.data) >= self.max_size:
                evicted = self.data[0]
                del self.keys_to_indices[evicted.key]
                i = 0
                self.data[0] = entry
            else:
                i = len(self.data)
                self.data.append(entry)
            self.keys_to_indices[key] = i
        else:
            entry = self.data[i]
            assert entry.key == key
            entry.value = value
            entry.score = self.on_access(entry.key, entry.value, entry.score)

        self.__balance(i)

        if evicted is not None:
            if self.data[0] is not entry:
                assert evicted.score <= self.data[0].score
            self.on_evict(evicted.key, evicted.value, evicted.score)

    def clear(self):
        del self.data[:]
        self.keys_to_indices.clear()

    def __repr__(self):
        return '{%s}' % (', '.join(
            '%r: %r' % (e.key, e.value) for e in self.data),)

    def new_entry(self, key, value):
        raise NotImplementedError()

    def on_access(self, key, value, score):
        return score

    def on_evict(self, key, value, score):
        pass

    def check_valid(self):
        for i, e in enumerate(self.data):
            assert self.keys_to_indices[e.key] == i
            for j in [i * 2 + 1, i * 2 + 2]:
                if j < len(self.data):
                    assert e.score <= self.data[j].score, self.data

    def __swap(self, i, j):
        assert i < j
        assert self.data[j].score < self.data[i].score
        self.data[i], self.data[j] = self.data[j], self.data[i]
        self.keys_to_indices[self.data[i].key] = i
        self.keys_to_indices[self.data[j].key] = j

    def __balance(self, i):
        while i > 0:
            parent = (i - 1) // 2
            if self.__out_of_order(parent, i):
                self.__swap(parent, i)
                i = parent
            else:
                break
        while True:
            children = [
                j for j in (2 * i + 1, 2 * i + 2)
                if j < len(self.data)
            ]
            if len(children) == 2:
                children.sort(key=lambda j: self.data[j].score)
            for j in children:
                if self.__out_of_order(i, j):
                    self.__swap(i, j)
                    i = j
                    break
            else:
                break

    def __out_of_order(self, i, j):
        assert i == (j - 1) // 2
        return self.data[j].score < self.data[i].score


class LRUCache(GenericCache):
    __slots__ = ('__tick',)

    def __init__(self, max_size):
        super(LRUCache, self).__init__(max_size)
        self.__tick = 0

    def new_entry(self, key, value):
        return self.tick()

    def on_access(self, key, value, score):
        return self.tick()

    def tick(self):
        self.__tick += 1
        return self.__tick


class LFUCache(GenericCache):
    def new_entry(self, key, value):
        return 1

    def on_access(self, key, value, score):
        return score + 1


class LFLRUCache(GenericCache):
    __slots__ = ('__tick',)

    def __init__(self, max_size, ):
        super(LFLRUCache, self).__init__(max_size)
        self.__tick = 0

    def tick(self):
        self.__tick += 1
        return self.__tick

    def new_entry(self, key, value):
        return [1, self.tick()]

    def on_access(self, key, value, score):
        score[0] += 1
        score[1] = self.tick()
        return score
