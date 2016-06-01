# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

from weakref import ref as weakref
from weakref import WeakKeyDictionary
from functools import wraps


class BaseTag(object):

    def __repr__(self):
        return 'BASE_TAG'

BASE_TAG = BaseTag()


class Grammar(object):
    __hash = None

    def __hash__(self):
        if self.__hash is None:
            if isinstance(self, Epsilon):
                self.__hash = hash(('Epsilon', self.tags))
            elif isinstance(self, Literal):
                self.__hash = hash(('Literal', self.string))
            elif isinstance(self, Star):
                self.__hash = hash(('Star', self.repeated))
            elif isinstance(self, Cat):
                self.__hash = hash(('Cat', self.left, self.right))
            elif isinstance(self, Nil):
                return 0
            else:
                assert isinstance(self, Alt)
                self.__hash = hash(('Alt', tuple(self.alternatives)))
        return self.__hash

    def __eq__(self, other):
        return isinstance(other, Grammar) and self.__cmp__(other) == 0

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __gt__(self, other):
        return self.__cmp__(other) < 0

    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0

    def __cmp__(self, other):
        if self is other:
            return 0
        if not isinstance(other, Grammar):
            raise TypeError('Can only compare Grammar with Grammar, not %s' % (
                type(other).__name__
            ))
        si = type_ordering[type(self)]
        oi = type_ordering[type(other)]
        if si < oi:
            return -1
        elif si > oi:
            return 1
        if isinstance(self, Nil):
            return 0
        if isinstance(self, Epsilon):
            if self.tags == other.tags:
                return 0
            if len(self.tags) < len(other.tags):
                return -1
            if len(self.tags) > len(other.tags):
                return 1
            sk = sorted(self.tags, key=lambda s: (type(s).__name__, s))
            ok = sorted(other.tags, key=lambda s: (type(s).__name__, s))
            if sk < ok:
                return -1
            else:
                assert sk > ok
                return 1
        if isinstance(self, Literal):
            sk = (len(self.string), self.string)
            ok = (len(other.string), other.string)
            if sk < ok:
                return -1
            if sk == ok:
                return 0
            if sk > ok:
                return 1
        if isinstance(self, Star):
            return self.repeated.__cmp__(other.repeated)
        if isinstance(self, Cat):
            l = self.left.__cmp__(other.left)
            if l != 0:
                return l
            return self.right.__cmp__(other.right)
        assert isinstance(self, Alt)
        if len(self.alternatives) < len(other.alternatives):
            return -1
        if len(self.alternatives) > len(other.alternatives):
            return 1
        for u, v in zip(self.alternatives, other.alternatives):
            l = u.__cmp__(v)
            if l != 0:
                return l
        return 0


class Star(Grammar):

    def __init__(self, repeated):
        self.repeated = repeated

    def __repr__(self):
        return 'star(%r)' % (self.repeated,)


class Cat(Grammar):

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return 'cat(%r, %r)' % (self.left, self.right)


class Alt(Grammar):

    def __init__(self, alternatives):
        self.alternatives = tuple(alternatives)

    def __repr__(self):
        return 'alt(%s)' % (', '.join(map(repr, self.alternatives)),)


class Literal(Grammar):

    def __repr__(self):
        return 'literal(%r)' % (self.string,)

    def __init__(self, string):
        self.string = string


class Epsilon(Grammar):

    def __init__(self, tags):
        self.tags = frozenset(tags) | frozenset((BASE_TAG,))

    def __repr__(self):
        return 'epsilon(%s)' % (', '.join(map(repr, self.tags)),)


class Nil(Grammar):

    def __repr__(self):
        return 'nil()'


type_ordering = dict((x, i) for i, x in enumerate([
    Epsilon, Literal, Star, Cat, Alt, Nil
]))


def cached_property(function):
    @wraps(function)
    def accept(self, grammar):
        grammar = self.normalize(grammar)
        key = (function, weakref(grammar))
        try:
            return self._GrammarTable__property_cache[key]
        except KeyError:
            result = function(self, grammar)
            self._GrammarTable__property_cache[key] = result
            return result
    return accept


class GrammarTable(object):

    def __init__(self):
        self.__value_cache = WeakKeyDictionary()
        self.__states = []
        self.__transitions = []
        self.__nil = Nil()
        self.__property_cache = {}
        self.__derivatives = WeakKeyDictionary()

    def derivative(self, grammar, character):
        if isinstance(grammar, (Nil, Epsilon)):
            return self.__nil
        cache = self.__derivatives.setdefault(grammar, {})
        try:
            return cache[character]
        except KeyError:
            pass
        if isinstance(grammar, Literal):
            if grammar.string and grammar.string[0] == character:
                result = Literal(grammar.string[1:])
            else:
                result = self.__nil
        elif isinstance(grammar, Star):
            result = Cat(
                self.derivative(grammar.repeated, character), grammar)
        elif isinstance(grammar, Alt):
            result = Alt(
                self.derivative(a, character) for a in grammar.alternatives
            )
        else:
            assert isinstance(grammar, Cat)
            result = Cat(
                self.derivative(grammar.left, character), grammar.right)
            if self.can_match_empty(grammar.left):
                result = Alt((
                    result, self.derivative(grammar.right, character)))
        result = self.normalize(result)
        cache[character] = result
        return result

    def normalize(self, grammar):
        return self.__to_state_and_normalized(grammar)[0]

    def state(self, grammar):
        return self.__to_state_and_normalized(grammar)[1]

    def transitions(self, state):
        grammar = self.__states[state]
        while len(self.__transitions) <= state:
            self.__transitions.append(None)
        if self.__transitions[state] is None:
            self.__transitions[state] = dict(
                (c, self.derivative(grammar, c))
                for c in self.valid_starts(grammar)
            )
        return self.__transitions[state]

    def tags(self, state):
        return self.reachable_tags(self.__states[state])

    @cached_property
    def match_empty(self, grammar):
        if isinstance(grammar, Nil):
            return None
        if isinstance(grammar, Epsilon):
            return grammar.tags
        if isinstance(grammar, Star):
            child_result = self.match_empty(grammar.repeated)
            return child_result or frozenset((BASE_TAG,))
        if isinstance(grammar, Cat):
            lr = self.match_empty(grammar.left)
            if lr is None:
                return None
            else:
                rr = self.match_empty(grammar.right)
                if rr is None:
                    return None
                else:
                    return lr | rr
        if isinstance(grammar, Literal):
            if grammar.string:
                return None
            else:
                return frozenset((BASE_TAG,))
        assert isinstance(grammar, Alt)
        result = None
        for a in grammar.alternatives:
            partial = self.match_empty(a)
            if partial is not None:
                if result is None:
                    result = partial
                else:
                    result |= partial
        return result

    def can_match_empty(self, grammar):
        return self.match_empty(grammar) is not None

    @cached_property
    def valid_starts(self, grammar):
        if isinstance(grammar, (Nil, Epsilon)):
            return frozenset()
        if isinstance(grammar, Star):
            return self.valid_starts(grammar.repeated)
        if isinstance(grammar, Literal):
            return frozenset(grammar.string[:1])
        if isinstance(grammar, Cat):
            if self.can_match_empty(grammar.left):
                return self.valid_starts(grammar.left) | self.valid_starts(
                    grammar.right)
            else:
                return self.valid_starts(grammar.left)
        assert isinstance(grammar, Alt)
        result = set()
        for a in grammar.alternatives:
            result.update(self.valid_starts(a))
        return frozenset(result)

    @cached_property
    def reachable_tags(self, grammar):
        if isinstance(grammar, (Nil, Literal)):
            return frozenset()
        if isinstance(grammar, Star):
            return self.reachable_tags(grammar.repeated) | frozenset(
                (BASE_TAG,))
        if isinstance(grammar, Epsilon):
            return grammar.tags
        if isinstance(grammar, Cat):
            result = set()
            if self.can_match_empty(grammar.left):
                result.update(self.reachable_tags(grammar.right))
            if self.can_match_empty(grammar.right):
                result.update(self.reachable_tags(grammar.left))
            return frozenset(result)
        assert isinstance(grammar, Alt)
        result = set()
        for a in grammar.alternatives:
            result.update(self.reachable_tags(a))
        return result

    def __to_state_and_normalized(self, grammar):
        try:
            return self.__value_cache[grammar]
        except KeyError:
            normalized = self.__do_normalize(grammar)
            if normalized != grammar:
                result = self.__to_state_and_normalized(normalized)
            else:
                i = len(self.__states)
                self.__states.append(grammar)
                result = (grammar, i)
                self.__value_cache[grammar] = result
            return result

    def __do_normalize(self, grammar):
        """Giant term rewriting system to try to collapse the whole range of
        grammars into a much more manageable subset."""
        if isinstance(grammar, Nil):
            return self.__nil
        if isinstance(grammar, Epsilon):
            return grammar
        if isinstance(grammar, Literal):
            if grammar.string:
                return grammar
            return self.normalize(Epsilon(frozenset()))
        if isinstance(grammar, Cat):
            left = self.normalize(grammar.left)
            right = self.normalize(grammar.right)
            if isinstance(left, Nil) or isinstance(right, Nil):
                return self.__nil
            elif isinstance(left, Epsilon):
                if isinstance(right, Epsilon):
                    return self.normalize(Epsilon(
                        left.tags | right.tags
                    ))
                elif not self.can_match_empty(right):
                    return right
            elif isinstance(left, Literal):
                if isinstance(right, Literal):
                    return self.normalize(Literal(left.string + right.string))
                elif isinstance(right, Cat) and isinstance(
                    right.left, Literal
                ):
                    return self.normalize(Cat(
                        Literal(left.string + right.left.string), right.right))
            elif isinstance(left, Cat):
                return self.normalize(Cat(left.left, Cat(left.right, right)))
            if left is grammar.left and right is grammar.right:
                return grammar
            else:
                return Cat(left, right)
        if isinstance(grammar, Star):
            repeated = self.normalize(grammar.repeated)
            if isinstance(repeated, (Star, Epsilon)):
                return repeated
            if repeated is grammar.repeated:
                return grammar
            else:
                return Star(repeated)
        assert isinstance(grammar, Alt)
        alternatives = set()
        for a in grammar.alternatives:
            a = self.normalize(a)
            if isinstance(a, Alt):
                alternatives.update(a.alternatives)
            elif not isinstance(a, Nil):
                alternatives.add(a)
        alternatives = sorted(alternatives)
        if len(alternatives) == 0:
            return self.__nil
        if len(alternatives) == 1:
            return alternatives[0]
        if alternatives == grammar.alternatives:
            return grammar
        return Alt(alternatives)


def nil():
    return Nil()


def epsilon(*tags):
    return Epsilon(tags)


def alt(*alternatives):
    return Alt(alternatives)


def cat(*parts):
    result = None
    for p in reversed(parts):
        if result is None:
            result = p
        else:
            result = Cat(p, result)
    if result is None:
        return epsilon()
    else:
        return result


def star(repeated):
    return Star(repeated)


def literal(string):
    return Literal(string)
