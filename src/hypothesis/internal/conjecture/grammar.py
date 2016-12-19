# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2016 David R. MacIver
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

NORMALIZATION_CACHE = {}


def _clear_cache():
    NORMALIZATION_CACHE.clear()


class Grammar(object):

    def __init__(self):
        self.__normalizes_to = None
        self.normalized = False
        self.__initial_values = None
        self.__derivatives = {}

    @property
    def has_matches(self):
        return self.matches_empty or self.matches_non_empty

    def derivative(self, b):
        if b not in self.initial_values():
            return Nil
        try:
            return self.__derivatives[b]
        except KeyError:
            pass

        r = self._calculate_derivative(b).normalize()
        self.__derivatives[b] = r
        return r

    def initial_values(self):
        if self.__initial_values is None:
            self.__initial_values = tuple(sorted(frozenset(
                self._calculate_initial_values()
            )))
        return self.__initial_values

    def __cmp__(self, other):
        if self is other:
            return 0
        if type(self) != type(other):
            ss = ORDER_SCORES[type(self)]
            so = ORDER_SCORES[type(self)]
            if ss < so:
                return -1
            else:
                return 1
        return self._do_cmp(other)

    def __eq__(self, other):
        if not isinstance(other, Grammar):
            return NotImplemented
        if self is other:
            return True
        if self.normalized and other.normalized:
            return False
        return self.__cmp__(other) == 0

    def __ne__(self, other):
        if not isinstance(other, Grammar):
            return NotImplemented
        return not self.__eq__(other)

    def __lt__(self, other):
        if not isinstance(other, Grammar):
            return NotImplemented
        return self.__cmp__(other) < 0

    def __gt__(self, other):
        if not isinstance(other, Grammar):
            return NotImplemented
        return self.__cmp__(other) > 0

    def __le__(self, other):
        if not isinstance(other, Grammar):
            return NotImplemented
        return self.__cmp__(other) <= 0

    def __ge__(self, other):
        if not isinstance(other, Grammar):
            return NotImplemented
        return self.__cmp__(other) >= 0

    def normalize(self):
        if self.normalized:
            return self
        elif self.__normalizes_to is not None:
            return self.__normalizes_to
        else:
            try:
                result = NORMALIZATION_CACHE[self]
            except KeyError:
                result = self._do_normalize()
                try:
                    result = NORMALIZATION_CACHE[self]
                except KeyError:
                    result.normalized = True
                    NORMALIZATION_CACHE[self] = result
            self.__normalizes_to = result
            return result


class Literal(Grammar):
    normalized = False

    def __init__(self, value):
        Grammar.__init__(self)
        self.value = value

    @property
    def matches_empty(self):
        return len(self.value) == 0

    @property
    def matches_non_empty(self):
        return len(self.value) > 0

    def _do_cmp(self, other):
        if self.value == other.value:
            return 0
        if len(self.value) < len(other.value):
            return -1
        if len(self.value) > len(other.value):
            return -1
        if self.value < other.value:
            return -1
        else:
            assert self.value > other.value
            return 1

    def _calculate_initial_values(self):
        if self.value:
            yield self.value[0]

    def __hash__(self):
        return hash(self.value)

    def _do_normalize(self):
        return self

    def _calculate_derivative(self, b):
        assert b == self.value[0]
        return Literal(self.value[1:])


class BranchGrammar(Grammar):

    def _do_cmp(self, other):
        if len(self.children) < len(other.value):
            return -1
        if len(self.children) > len(other.value):
            return -1
        for u, v in zip(self.children, other.children):
            c = u.__cmp__(v)
            if c != 0:
                return c
        return 0


class Concatenation(BranchGrammar):

    def __init__(self, children):
        Grammar.__init__(self)
        self.children = tuple(children)
        assert self.children
        self.matches_empty = all(c.matches_empty for c in self.children)
        self.matches_non_empty = any(
            c.matches_non_empty for c in self.children)

    def __hash__(self):
        h = hash(len(self.children))
        for c in self.children:
            h *= 31
            h += hash(c)
        return h

    def _do_normalize(self):
        children = []
        for c in self.children:
            c = c.normalize()
            if c is Nil:
                return Nil
            if isinstance(c, Concatenation):
                children.extend(c.children)
            elif isinstance(c, Literal) and not c.value:
                pass
            elif (
                isinstance(c, Literal) and children and
                isinstance(children[-1], Literal)
            ):
                children[-1] = Literal(children[-1].value + c.value)
            else:
                children.append(c)
        if len(children) == 1:
            return children[0]
        else:
            return Concatenation(children)

    def _calculate_initial_values(self):
        result = set()
        for c in self.children:
            result.update(c.initial_values())
            if not c.matches_empty:
                break
        return result

    def _calculate_derivative(self, b):
        parts = []
        for i, c in enumerate(self.children):
            parts.append(Concatenation(
                (c.derivative(b),) + self.children[i + 1:]))
            if not c.matches_empty:
                break
        return Alternation(parts)


class Alternation(BranchGrammar):

    def __init__(self, children):
        Grammar.__init__(self)
        self.children = tuple(children)
        self.matches_empty = any(c.matches_empty for c in self.children)
        self.matches_non_empty = any(
            c.matches_non_empty for c in self.children)

    def __hash__(self):
        h = hash(len(self.children))
        for c in self.children:
            h ^= hash(c)
        return h

    def _do_normalize(self):
        children = set()
        for c in self.children:
            c = c.normalize()
            if c is Nil:
                pass
            elif isinstance(c, Alternation):
                children.update(c.children)
            else:
                children.add(c)
        if not children:
            return Nil
        else:
            children = sorted(children)
            if len(children) > 1:
                return Alternation(children)
            else:
                return children[0]

    def _calculate_initial_values(self):
        result = set()
        for c in self.children:
            result.update(c.initial_values())
        return result

    def _calculate_derivative(self, b):
        return Alternation(c.derivative(b) for c in self.children)


class Star(Grammar):

    def __init__(self, child):
        Grammar.__init__(self)
        self.child = child
        self.matches_non_empty = self.child.matches_non_empty

    @property
    def matches_empty(self):
        return True

    def _do_cmp(self, other):
        return self.child.__cmp__(other)

    def __hash__(self):
        return ~hash(self.child)

    def _do_normalize(self):
        c = self.child.normalize()
        if isinstance(c, Star):
            return c
        elif c is Nil:
            return Epsilon
        else:
            return Star(c)

    def _calculate_initial_values(self):
        return self.child.initial_values()

    def _calculate_derivative(self, b):
        return Concatenation((self.child.derivative(b), self))


class _Nil(Grammar):

    def __init__(self):
        Grammar.__init__(self)
        self.normalized = True
        self.matches_empty = False
        self.matches_non_empty = False

    def __hash__(self):
        return 4

    def _do_cmp(self):
        assert False

    def _calculate_initial_values(self):
        return frozenset()

    def _calculate_derivative(self, b):
        return self


Nil = _Nil()

Epsilon = Literal(b'').normalize()


ORDER_SCORES = {
    _Nil: 0,
    Literal: 1,
    Star: 2,
    Alternation: 3,
    Concatenation: 4,
}


class Mixture(object):

    def __init__(self, weighted_grammars):
        norm = {}
        for g, w in weighted_grammars:
            if w > 0:
                g = g.normalize()
                norm[g] = norm.get(g, 0) + w
        norm.pop(Nil, None)
        self.weighted_grammars = tuple(sorted(norm.items()))
        self.__weights = None
        self.__stop_weight = None
        self.__derivatives = {}
        self.matches_empty = any(
            g.matches_empty for g, _ in self.weighted_grammars)
        self.matches_non_empty = any(
            g.matches_non_empty for g, _ in self.weighted_grammars)

    @property
    def has_matches(self):
        return len(self.weighted_grammars) > 0

    def derivative(self, b):
        try:
            return self.__derivatives[b]
        except KeyError:
            pass
        result = Mixture(
            (g.derivative(b), w) for g, w in self.weighted_grammars)
        self.__derivatives[b] = result
        return result

    @property
    def weights(self):
        if self.__weights is None:
            weights = [0] * 256
            for w, g in self.weighted_grammars:
                vs = w.initial_values()
                for v in vs:
                    weights[v] += g / len(vs)
            while weights and not weights[-1]:
                weights.pop()
            self.__weights = weights
        return self.__weights

    @property
    def stop_weight(self):
        if self.__stop_weight is None:
            can_stop = 0
            total = 0
            for w, g in self.weighted_grammars:
                total += g
                if w.matches_empty:
                    can_stop += g
            self.__stop_weight = can_stop / total
        return self.__stop_weight

    def __eq__(self, other):
        if not isinstance(other, Mixture):
            return NotImplemented
        return self.weighted_grammars == other.weighted_grammars

    def __ne__(self, other):
        if not isinstance(other, Mixture):
            return NotImplemented
        return self.weighted_grammars != other.weighted_grammars

    def __hash__(self):
        return hash(self.weighted_grammars)
