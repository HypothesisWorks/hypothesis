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

import heapq
import types
import functools
from collections import deque

from hypothesis.internal.compat import hbytes, hrange


def tupleize(args):
    result = []
    for a in args:
        if isinstance(a, (tuple, list, types.GeneratorType)):
            a = tuple(a)
        if isinstance(a, set):
            a = frozenset(a)
        result.append(a)
    return tuple(result)


def cached(function):
    cache = {}

    @functools.wraps(function)
    def accept(*args):
        args = tupleize(args)
        try:
            return cache[args]
        except KeyError:
            pass
        result = function(*args)
        cache[args] = result
        if isinstance(result, Grammar) and not result.has_matches():
            result = Nil
            cache[args] = result
        return result
    return accept


class Grammar(object):

    def __init__(self):
        self.__initial_values = None
        self.__derivatives = {}
        self.__has_matches = None
        self.__weights = None
        self.__choices = None

    def weights(self):
        if self.__weights is None:
            choices = tuple(sorted(self.initial_values()))
            tmp = [0] * len(choices)
            for i, c in enumerate(choices):
                tmp[i] = 1
            self.__weights = tuple(tmp)
            self.__choices = choices
        return self.__weights

    def choices(self):
        self.weights()
        return self.__choices

    def has_matches(self):
        if self._always_has_matches:
            return True
        if self.__has_matches is None:
            self.__has_matches = self.__calculate_has_matches()
        return self.__has_matches

    def matches(self, buf):
        remainder = self
        for b in buf:
            remainder = remainder.derivative(b)
        return remainder.matches_empty

    @property
    def _always_has_matches(self):
        return self.matches_empty

    def __calculate_has_matches(self):
        # Perform a breadth first search of reading characters from the
        # grammar until we either run into something we know we can match
        # or we exhaust all possible derivatives and conclude that matching
        # is impossible
        queue = []
        heapq.heappush(queue, (0, self))
        while queue:
            n, g = heapq.heappop(queue)
            for c in sorted(g.initial_values()):
                child = g.derivative(c)
                if child.__has_matches or child._always_has_matches:
                    return True
                heapq.heappush(queue, (n + 1, child))
        return False

    def smallest_match(self):
        queue = deque()
        queue.append((self, ()))
        seen = set()
        while queue:
            grammar, path = queue.popleft()
            if grammar in seen:
                continue
            seen.add(grammar)
            if grammar.matches_empty:
                result = bytearray()
                while path:
                    path, c = path
                    result.append(c)
                result.reverse()
                return hbytes(result)
            if grammar.has_matches():
                for c in sorted(grammar.initial_values()):
                    queue.append((grammar.derivative(c), (path, c)))
        return None

    def derivative(self, b):
        if b not in self.initial_values():
            return Nil
        try:
            return self.__derivatives[b]
        except KeyError:
            pass

        r = self._calculate_derivative(b)
        if not r.has_matches():
            r = Nil
        self.__derivatives[b] = r
        return r

    def initial_values(self):
        if self.__initial_values is None:
            result = frozenset(
                self._calculate_initial_values()
            )
            assert all(isinstance(i, int) for i in result), self
            self.__initial_values = result
            self.__initial_values = frozenset(
                c for c in result
                if self.derivative(c) is not Nil
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
        result = self._do_cmp(other)
        assert result != 0
        return result

    def __eq__(self, other):
        if not isinstance(other, Grammar):
            return NotImplemented
        return self is other

    def __hash__(self):
        return hash(id(self))

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


class _Literal(Grammar):

    def __init__(self, value):
        Grammar.__init__(self)
        assert isinstance(value, hbytes), value
        self.value = value

    @property
    def _always_has_matches(self):
        return True

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

    def _do_normalize(self):
        return self

    def _calculate_derivative(self, b):
        assert b == self.value[0]
        return Literal(self.value[1:])

    def __repr__(self):
        return 'Literal(%r)' % (self.value,)


@cached
def Literal(value):
    if len(value) == 1:
        return Charset(tuple(value))
    else:
        return _Literal(value)


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


class _Negation(Grammar):

    def __init__(self, child):
        Grammar.__init__(self)
        self.child = child

    @property
    def matches_empty(self):
        return not self.child.matches_empty

    def _do_cmp(self, other):
        return self.child.__cmp__(other)

    def _calculate_initial_values(self):
        return ALL_BYTES

    def _calculate_derivative(self, b):
        return Negation(self.child.derivative(b))

    def __repr__(self):
        return 'Negation(%s)' % (self.child,)


@cached
def Negation(child):
    if isinstance(child, _Negation):
        return child.child
    if not child.has_matches():
        return Everything
    if child is Everything:
        return Nil
    if isinstance(child, _Intersection):
        return Alternation(Negation(c) for c in child)
    return _Negation(child)


class _Concatenation(Grammar):

    def __init__(self, left, right):
        Grammar.__init__(self)
        self.left = left
        self.right = right
        self.matches_empty = (
            self.left.matches_empty and self.right.matches_empty)
        self.__always_has_matches = (
            self.left._always_has_matches and self.right._always_has_matches)

    def _do_cmp(self, other):
        c = self.left.__cmp__(other.left)
        if c != 0:
            return c
        return self.right.__cmp__(other.right)

    def _always_has_matches(self):
        return self.__always_has_matches

    def _calculate_initial_values(self):
        result = set(self.left.initial_values())
        if self.left.matches_empty:
            result.update(self.right.initial_values())
        return result

    def _calculate_derivative(self, b):
        base = Concatenation((self.left.derivative(b), self.right))
        if self.left.matches_empty:
            base = Alternation((self.right.derivative(b), base))
        return base

    def __repr__(self):
        return 'Concatenation(%r, %r)' % (self.left, self.right)


@cached
def base_concatenation(renormalized):
    if len(renormalized) == 0:
        return Epsilon
    if len(renormalized) == 1:
        return renormalized[0]
    else:
        return _Concatenation(renormalized[0], base_concatenation(
            renormalized[1:]))


@cached
def Concatenation(children):
    renormalized = []

    for c in children:
        if c is Nil:
            return Nil
        if isinstance(c, _Concatenation):
            renormalized.append(c.left)
            renormalized.append(c.right)
        elif isinstance(c, _Literal) and not c.value:
            pass
        elif (
            isinstance(c, _Literal) and renormalized and
            isinstance(renormalized[-1], _Literal)
        ):
            renormalized[-1] = Literal(renormalized[-1].value + c.value)
        elif (
            isinstance(c, _Wildcard) and renormalized and
            isinstance(renormalized[-1], _Wildcard)
        ):
            renormalized[-1] = Wildcard(renormalized[-1].length + c.length)
        else:
            renormalized.append(c)
    return base_concatenation(renormalized)


class _Alternation(BranchGrammar):

    def __init__(self, children):
        Grammar.__init__(self)
        self.children = tuple(children)
        self.matches_empty = any(c.matches_empty for c in self.children)
        self.__always_has_matches = any(
            c._always_has_matches for c in self.children)

    def _always_has_matches(self):
        return self.__always_has_matches

    def _calculate_initial_values(self):
        result = set()
        for c in self.children:
            result.update(c.initial_values())
        return result

    def _calculate_derivative(self, b):
        return Alternation(c.derivative(b) for c in self.children)

    def __repr__(self):
        return 'Alternation(%s)' % (self.children,)


class _Bagged(Grammar):

    def __init__(self, children, matches_empty):
        Grammar.__init__(self)
        self.children = dict(children)
        self.matches_empty = matches_empty
        self.__always_has_matches = matches_empty or any(
            c._always_has_matches for c in self.children.values())

    def _do_cmp(self, other):
        if self.matches_empty and not other.matches_empty:
            return -1
        if other.matches_empty and not self.matches_empty:
            return 1
        if len(self.children) < len(other.children):
            return -1
        if len(self.children) > len(other.children):
            return -1
        for (a, u), (b, v) in zip(
            sorted(self.children.items()),
            sorted(other.children.items()),
        ):
            if a < b:
                return -1
            if b < a:
                return 1
            t = u.__cmp__(v)
            if t != 0:
                return t
        return 0

    def _always_has_matches(self):
        return self.__always_has_matches

    def _calculate_initial_values(self):
        return frozenset(self.children)

    def _calculate_derivative(self, b):
        return self.children.get(b, Nil)

    def __repr__(self):
        return 'Bagged(%r, %r)' % (self.children, self.matches_empty)


@cached
def Char(c):
    return Literal(hbytes([c]))


@cached
def base_bagged(parts, matches_empty):
    return _Bagged(parts, matches_empty)


@cached
def bagged(renormalized):
    tmp = _Alternation(renormalized)
    parts = []
    for c in tmp.initial_values():
        r = tmp.derivative(c)
        if r.has_matches():
            parts.append((c, r))
    return base_bagged(sorted(parts), tmp.matches_empty)


@cached
def base_alternation(renormalized):
    if not renormalized:
        return Nil
    elif len(renormalized) > 1:
        return _Alternation(renormalized)
    else:
        return renormalized[0]


class _Charset(Grammar):

    def __init__(self, chars):
        Grammar.__init__(self)
        self.chars = frozenset(chars)
        assert all(isinstance(i, int) for i in self.chars), self.chars

    def __repr__(self):
        return 'Charset(%r)' % (tuple(sorted(self.chars)),)

    @property
    def matches_empty(self):
        return False

    @property
    def _always_has_matches(self):
        return True

    def _calculate_initial_values(self):
        return self.chars

    def _calculate_derivative(self, b):
        if b in self.chars:
            return Epsilon
        else:
            return Nil

    def _do_cmp(self, other):
        if len(self.chars) < len(other.chars):
            return -1
        if len(self.chars) > len(other.chars):
            return 1
        c1 = sorted(self.chars)
        c2 = sorted(other.chars)
        if c1 < c2:
            return -1
        else:
            assert c1 > c2
            return 1


@cached
def Charset(chars):
    if not isinstance(chars, frozenset):
        return Charset(frozenset(chars))
    if not chars:
        return Nil
    return _Charset(chars)


@cached
def Alternation(children):
    children = tuple(children)
    if len(children) == 1:
        return children[0]
    if not len(children):
        return Nil

    use_bag = False

    single_chars = set()

    renormalized = set()
    for c in children:
        if not c.has_matches():
            pass
        elif c is Everything:
            return Everything
        elif isinstance(c, _Alternation):
            renormalized.update(c.children)
        elif isinstance(c, _Bagged):
            use_bag = True
            renormalized.add(c)
        elif isinstance(c, _Charset):
            single_chars.update(c.chars)
        else:
            renormalized.add(c)

    if single_chars:
        renormalized.add(Charset(single_chars))

    renormalized = tuple(sorted(renormalized))

    if len(renormalized) > 10 or use_bag:
        return bagged(renormalized)
    else:
        return base_alternation(renormalized)


class _Wildcard(Grammar):

    def __init__(self, length):
        Grammar.__init__(self)
        assert length > 0
        self.length = length

    @property
    def _always_has_matches(self):
        return True

    @property
    def matches_empty(self):
        return False

    def _do_cmp(self, other):
        if self.length < other.length:
            return -1
        if self.length > other.length:
            return 1
        return 0

    def _calculate_initial_values(self):
        return ALL_BYTES

    def _calculate_derivative(self, b):
        if self.length > 1:
            return Wildcard(self.length - 1)
        else:
            return Epsilon

    def __repr__(self):
        return 'Wildcard(%s)' % (self.length,)


@cached
def Wildcard(length):
    return _Wildcard(length)


ALL_BYTES = frozenset(range(256))


class _Intersection(BranchGrammar):

    def __init__(self, children):
        Grammar.__init__(self)
        self.children = tuple(children)
        self.matches_empty = all(c.matches_empty for c in self.children)

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


@cached
def base_intersection(children):
    if not children:
        return Everything
    if len(children) == 1:
        return children[0]
    result = _Intersection(children)
    if not result.has_matches():
        return Nil
    elif not result.initial_values():
        assert result.matches_empty
        return Epsilon
    elif len(result.initial_values()) == 1:
        c = list(result.initial_values())[0]
        return Concatenation((
            Char(c), result.derivative(c)
        ))
    else:
        return result


@cached
def Intersection(children):
    renormalized = set()
    for c in children:
        if c is Nil:
            return Nil
        elif c is Everything:
            pass
        elif isinstance(c, _Intersection):
            renormalized.update(c.children)
        else:
            renormalized.add(c)
    return base_intersection(sorted(renormalized))


class _Star(Grammar):

    def __init__(self, child):
        Grammar.__init__(self)
        self.child = child

    @property
    def matches_empty(self):
        return True

    def _do_cmp(self, other):
        return self.child.__cmp__(other)

    def _calculate_initial_values(self):
        return self.child.initial_values()

    def _calculate_derivative(self, b):
        return Concatenation((self.child.derivative(b), self))

    def __repr__(self):
        return 'Star(%r)' % (self.child,)


@cached
def Star(child):
    if isinstance(child, _Star):
        return child
    if child is Epsilon:
        return child
    if child is Nil:
        return child
    if child is Everything:
        return child
    return _Star(child)


class _Nil(Grammar):

    def __init__(self):
        Grammar.__init__(self)
        self.matches_empty = False

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
        self.matches_empty = True

    def _do_cmp(self):
        assert False

    def _calculate_initial_values(self):
        return ALL_BYTES

    def _calculate_derivative(self, b):
        return self

    def __repr__(self):
        return 'Everything'


class _Interval(Grammar):

    def __init__(self, lower, upper):
        Grammar.__init__(self)
        assert len(lower) == len(upper) != 0
        assert lower <= upper
        assert isinstance(lower, hbytes)
        assert isinstance(upper, hbytes)
        self.upper = upper
        self.lower = lower

    @property
    def matches_empty(self):
        return False

    @property
    def _always_has_matches(self):
        return True

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
            return Interval(ln, hbytes([255] * len(ln)))
        elif b == self.upper[0]:
            un = self.upper[1:]
            return Interval(hbytes([0] * len(un)), un)
        else:
            assert self.lower[0] < b < self.upper[0]
            return Wildcard(len(self.lower) - 1)

    def __repr__(self):
        return 'Interval(%r, %r)' % (self.lower, self.upper)


@cached
def Interval(lower, upper):
    assert lower <= upper
    assert len(lower) == len(upper)
    if lower == upper:
        return Literal(lower)
    if len(lower) == 1:
        return Charset(hrange(lower[0], upper[0] + 1))

    prefix = 0
    while True:
        if lower[prefix] != upper[prefix]:
            break
        prefix += 1
    assert prefix < len(lower)
    if prefix > 0:
        return Concatenation((
            Literal(lower[:prefix]),
            Interval(lower[:prefix], upper[:prefix]),
        ))
    return _Interval(lower, upper)

Nil = _Nil()
Everything = _Everything()
Epsilon = Literal(hbytes(b''))

ORDER_SCORES = {}

for i, c in enumerate([
    _Nil,
    _Everything,
    _Wildcard,
    _Literal,
    _Charset,
    _Interval,
    _Negation,
    _Star,
    _Bagged,
    _Alternation,
    _Concatenation,
    _Intersection,
]):
    ORDER_SCORES[c] = i
