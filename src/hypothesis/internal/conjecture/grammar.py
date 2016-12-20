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
            self.__initial_values = frozenset(
                self._calculate_initial_values()
            )
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

    def __repr__(self):
        return 'Literal(%r)' % (self.value,)


class BranchGrammar(Grammar):

    def _do_cmp(self, other):
        if len(self.children) < len(other.children):
            return -1
        if len(self.children) > len(other.children):
            return -1
        for u, v in zip(self.children, other.children):
            c = u.__cmp__(v)
            if c != 0:
                return c
        return 0


class Negation(Grammar):

    def __init__(self, child):
        Grammar.__init__(self)
        self.child = child

    @property
    def matches_empty(self):
        return not self.child.matches_empty

    def _do_cmp(self, other):
        return self.child.__cmp__(other)

    def __hash__(self):
        return 1 + ~hash(self.child)

    def _do_normalize(self):
        c = self.child.normalize()
        if isinstance(c, Negation):
            return c.child
        elif c is Nil:
            return Everything
        elif c is Everything:
            return Nil
        else:
            return Negation(c)

    def _calculate_initial_values(self):
        return ALL_BYTES

    def _calculate_derivative(self, b):
        return Negation(self.child.derivative(b))

    def __repr__(self):
        return 'Negation(%s)' % (self.child,)


class Concatenation(BranchGrammar):

    def __init__(self, children):
        Grammar.__init__(self)
        self.children = tuple(children)
        assert self.children
        self.matches_empty = all(c.matches_empty for c in self.children)

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
            elif (
                isinstance(c, Wildcard) and children and
                isinstance(children[-1], Wildcard)
            ):
                children[-1] = Wildcard(children[-1].size + c.size)
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

    def __repr__(self):
        return 'Concatenation(%s)' % (self.children,)


class Alternation(BranchGrammar):

    def __init__(self, children):
        Grammar.__init__(self)
        self.children = tuple(children)
        self.matches_empty = any(c.matches_empty for c in self.children)

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

    def __repr__(self):
        return 'Alternation(%s)' % (self.children,)


class Wildcard(Grammar):

    def __init__(self, length):
        Grammar.__init__(self)
        assert length > 0
        self.length = length

    @property
    def matches_empty(self):
        return False

    def __hash__(self):
        return hash(self.length)

    def _do_cmp(self, other):
        if self.length < other.length:
            return -1
        if self.length > other.length:
            return 1
        return 0

    def _do_normalize(self):
        return self

    def _calculate_initial_values(self):
        return ALL_BYTES

    def _calculate_derivative(self, b):
        if self.length > 1:
            return Wildcard(self.length - 1)
        else:
            return Epsilon

    def __repr__(self):
        return 'Wildcard(%s)' % (self.length,)

ALL_BYTES = frozenset(range(256))


class Intersection(BranchGrammar):

    def __init__(self, children):
        Grammar.__init__(self)
        self.children = tuple(children)
        self.matches_empty = all(c.matches_empty for c in self.children)

    def __hash__(self):
        h = hash(len(self.children))
        for c in self.children:
            h ^= hash(c)
        return ~h

    def _do_normalize(self):
        # It requires a non-trivial amount of calculation to determine whether
        # an intersection type is non-empty. We don't do all of it at
        # normalization time, but this is a pretty good shortcut which will
        # often catch the basic cases.
        if not self.initial_values():
            if self.matches_empty:
                return Epsilon
            else:
                return Nil

        children = set()
        for c in self.children:
            c = c.normalize()
            if c is Nil:
                return Nil
            elif c is Everything:
                pass
            elif isinstance(c, Intersection):
                children.update(c.children)
            else:
                children.add(c)
        if not children:
            return Everything
        else:
            children = sorted(children)
            if len(children) > 1:
                return Intersection(children)
            else:
                return children[0]

    def _calculate_initial_values(self):
        result = None
        for c in self.children:
            if result is None:
                result = c.initial_values()
            else:
                result &= c.initial_values()
        return result

    def _calculate_derivative(self, b):
        return Intersection(c.derivative(b) for c in self.children)

    def __repr__(self):
        return 'Intersection(%r)' % (self.children,)


class Star(Grammar):

    def __init__(self, child):
        Grammar.__init__(self)
        self.child = child

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

    def __repr__(self):
        return 'Star(%r)' % (self.child,)


class _Nil(Grammar):

    def __init__(self):
        Grammar.__init__(self)
        self.normalized = True
        self.matches_empty = False

    def __hash__(self):
        return 4

    def _do_cmp(self):
        assert False

    def _calculate_initial_values(self):
        return frozenset()

    def _calculate_derivative(self, b):
        return self

    def __repr__(self):
        return 'Nil'


class _Everything(Grammar):

    def __init__(self):
        Grammar.__init__(self)
        self.normalized = True
        self.matches_empty = True

    def __hash__(self):
        return 7

    def _do_cmp(self):
        assert False

    def _calculate_initial_values(self):
        return ALL_BYTES

    def _calculate_derivative(self, b):
        return self

    def __repr__(self):
        return 'Everything'


class Interval(Grammar):

    def __init__(self, lower, upper):
        Grammar.__init__(self)
        assert len(lower) == len(upper) != 0
        assert lower <= upper
        self.upper = upper
        self.lower = lower

    @property
    def matches_empty(self):
        return False

    def __hash__(self):
        return hash((self.lower, self.upper))

    def _do_cmp(self, other):
        if len(self.lower) < len(other.lower):
            return -1
        if len(self.lower) > len(other.lower):
            return -1
        if self.lower < other.lower:
            return -1
        if self.lower > other.lower:
            return 1
        if self.upper < other.upper:
            return -1
        if self.upper > other.upper:
            return 1
        return 0

    def _calculate_initial_values(self):
        return range(self.lower[0], self.upper[0] + 1)

    def _calculate_derivative(self, b):
        if b < self.lower[0] or b > self.upper[0]:
            return Nil
        elif len(self.lower) == 1:
            return Epsilon
        elif b == self.lower[0] == self.upper[0]:
            ln = self.lower[1:]
            un = self.upper[1:]
            return Interval(ln, un)
        elif b == self.lower[0]:
            assert b < self.upper[0]
            ln = self.lower[1:]
            return Interval(ln, bytes([255] * len(ln)))
        elif b == self.upper[0]:
            un = self.upper[1:]
            return Interval(bytes([0] * len(un)), un)
        else:
            assert self.lower[0] < b < self.upper[0]
            return Wildcard(len(self.lower) - 1)

    def _do_normalize(self):
        if self.lower == self.upper:
            return Literal(self.lower).normalize()
        else:
            return self

    def __repr__(self):
        return 'Interval(%r, %r)' % (self.lower, self.upper)


Nil = _Nil()
Everything = _Everything()
Epsilon = Literal(b'').normalize()

ORDER_SCORES = {}

for i, c in enumerate([
    _Nil,
    Everything,
    Wildcard,
    Literal,
    Interval,
    Negation,
    Star,
    Alternation,
    Concatenation,
    Intersection,
]):
    ORDER_SCORES[c] = i
