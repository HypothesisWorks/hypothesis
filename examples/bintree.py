# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""This is a tutorial for building a strategy from scratch rather than using
the strategy combinators.

Note that the API described herein is "semi-public". This means it will not
break between patch releases but may break between minor versions. However
it should be pretty stable and usually it shouldn't break between minor
versions either, or will only do so in a fairly easy to fix way.

We're going to build a strategy for a binary tree with labelled leaves. That
is, every element of our data type is either a Leaf with a single value as a
label, or a Split which has a left and a right element that are themselves
binary trees.

Note: This file contains both tests and implementation, mostly for ease of
following. Normally you would of course separate these into their own files.

To run these tests, install pytest (ideally in a virtualenv) and from the root
of a hypothesis checkout run

PYTHONPATH=src python -m pytest examples/bintree.py

"""

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import math
from collections import namedtuple

from hypothesis import find, strategy
from hypothesis.strategies import just, lists, integers
from hypothesis.strategytests import strategy_test_suite
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.searchstrategy.strategies import check_length, \
    check_data_type


class BinaryTree(object):
    pass


class Leaf(BinaryTree):

    def __init__(self, label):
        self.label = label

    def __repr__(self):
        return 'Leaf(%r)' % (self.label,)

    def __eq__(self, other):
        return isinstance(other, Leaf) and self.label == other.label

    def __ne__(self, other):
        return not self.__eq__(other)


class Split(BinaryTree):

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return 'Split(%r, %r)' % (self.left, self.right)

    def __eq__(self, other):
        return (
            isinstance(other, Split) and
            self.left == other.left and
            self.right == other.right
        )

    def __ne__(self, other):
        return not self.__eq__(other)


class BinaryTreeStrategy(SearchStrategy):

    """An implementation of a strategy for generating BinaryTree instances.

    All methods specific to this implementation are prefixed with _, all
    others are implementing the SearchStrategy interface.

    """

    def __init__(self, leaf_strategy):
        """In order to create a strategy for binary trees, we need a strategy
        for creating labels for its leaves.

        Everything else we can handle ourselves.

        """
        super(BinaryTreeStrategy, self).__init__()
        self.leaf_strategy = leaf_strategy

    Parameter = namedtuple(
        'Parameter',
        ('size_control', 'split_location', 'leaf_parameter'),
    )

    def draw_parameter(self, random):
        """A parameter controls the "shape" of the data. Data generation
        proceeds by first drawing a parameter and then drawing a template given
        that parameter.

        This has two main benefits: Firstly, it lets us produce more
        interesting data, because the results are typically less uniform and
        more likely to trigger edge cases, and secondly it gives us a tool for
        shaping the exploration of the search space.

        Parameters can be any value at all. In this case we've defined a custom
        namedtuple to hold our data.

        """

        # Our parameter has three important details:
        return self.Parameter(
            # size_control will be used to determine how many leaves we
            # generate. We will use a geometric distribution, so the expected
            # number of leaves is 1 / size_control. As a result we set a lower
            # bound of 0.01 to prevent us from generating dangerously large
            # trees.
            size_control=max(0.01, random.random()),

            # split location will determine how balanced the tree is. The idea
            # will be that when splitting n nodes into a tree, we put roughly
            # split_location * n in the left hand side. Thus, if split_location
            # is around 0.5 the tree will be roughly balanced, but if it's near
            # 0 or 1 the tree will be very unbalanced.
            # Because python is bad at recursion and tends to have very short
            # stacks, we force this not to go too far to the edges so as to
            # keep the depth under control.
            split_location=0.2 + 0.8 * random.random(),

            # We need a parameter to control the shape of our leaf distribution
            # too. We use whatever the parameter normally associated with the
            # leaf strategy is. Note this is completely opaque to us: We can't
            # do anything with it except feed it back into the leaf strategy
            # later.
            leaf_parameter=self.leaf_strategy.draw_parameter(random)
        )

    def draw_template(self, random, parameter_value):
        """We now produce a template, which is a value that we will later turn
        into a binary tree.

        There are a number of reasons for the distinction which we won't
        go into here, but think of a template as an easier to work with
        intermediate representation of the final value. In particular
        templates are always hashable and comparable for equality, even
        if the finished product is not.

        """

        # Our templates will be tuples of 1 or 3 elements. A tuple of 1 element
        # is a leaf and will contain a leaf template, a tuple of 3 elements is
        # a split and will contain two BinaryTree templates followed by an int
        # which caches the number of leaf nodes in the tree. The reason for the
        # latter will become clear later.

        # Rather than attempt to do this recursively, we build a list of leaves
        # of a fixed size and then split that up into a tree. This allows us
        # much more control over the size of the finished product than we would
        # otherwise have.

        # This is 1 + a geometric distribution with parameter size_control.
        # It's 1 + because we don't allow our trees to be empty so we need at
        # least one element.
        n_leaf_labels = 1 + int(
            math.log(random.random()) /
            math.log1p(-parameter_value.size_control)
        )

        leaf_templates = tuple(
            self.leaf_strategy.draw_template(
                random, parameter_value.leaf_parameter)
            for _ in range(n_leaf_labels)
        )

        # We now need to need to figure out how to distribute the leaves.
        # We do this recursively, so farm off to another method.
        return self._split_leaf_list(
            leaf_templates, random, parameter_value.split_location
        )

    def _split_leaf_list(self, leaves, random, split_location):
        # Calling this on an empty list is a logical error.
        assert leaves

        if len(leaves) == 1:
            # If we have only one leaf then this is already the template for
            # a single node and we're done.
            return tuple(leaves)
        if len(leaves) == 2:
            # If we only have two, this can only be produced as a single split
            # with a leaf on either side.
            return (
                (leaves[0],), (leaves[1],), 2
            )
        # We now need to split the remaining leaves into two piles, one for the
        # left branch and one for the right. We first ensure that each pile is
        # non-empty and then distribute the remainder according to the
        # split_location parameter.

        left = [leaves[0]]
        right = [leaves[1]]
        for leaf in leaves[2:]:
            if random.random() <= split_location:
                left.append(leaf)
            else:
                right.append(leaf)

        left_template = self._split_leaf_list(left, random, split_location)
        right_template = self._split_leaf_list(right, random, split_location)

        # We now have two nice little piles of nodes to put on the left and
        # the right side of this split, and we must split those too.
        return self._make_split(
            left_template, right_template,
        )

    def _template_size(self, template):
        """Get the number of leaf nodes below a template."""
        if len(template) == 1:
            return 1
        else:
            return template[-1]

    def _make_split(self, left, right):
        """Smart constructor for a split template which handles getting the
        size right automatically."""
        return (
            left, right,
            self._template_size(left) + self._template_size(right)
        )

    def reify(self, template):
        """Reify is the point at which we take our templates and turn them into
        the values we actually want.

        Our templates here quite closely map to the desired end type, so
        all we have to do is make sure to reify the leaves and then
        assemble the templates into the appropriate BinaryTree subtype.

        """
        assert len(template) in (1, 3)
        if len(template) == 1:
            return Leaf(self.leaf_strategy.reify(template[0]))
        else:
            return Split(
                self.reify(template[0]), self.reify(template[1])
            )

    # At this point we can generate trees, and they will participate in the
    # adaptive assume nicely, but we can't save them to the database and they
    # won't simplify. This will tend to mean that our examples are very
    # complicated.
    # e.g. the following is from a find(BinaryTreeStrategy(strategy(())),
    # lambda x: True):
    # Split(Split(Leaf(()), Leaf(())), Leaf(()))

    # So we now need to define rules for simplifying.

    def simplifiers(self, random, template):
        """simplifiers are functions which take a pair (random, template) and
        return a generator over simpler versions of that template.

        Rather than each strategy having a single simplifier, strategies
        have many. This allows us to focus on only using simplifiers
        that work well for a particular problem, rather than continually
        trying ones that will never work.

        """
        # The purpose of the template argument is that it lets us skip
        # simplifiers we know will be useless for this particular template.
        # All simplifiers *must* work for every template, but "work" just means
        # doesn't error. It doesn't matter if they don't do anything useful.
        if len(template) == 3:
            # We first try passing to subtrees because this has the potential
            # to make the template a lot smaller, which we want to prioritise.
            # In general you want to leave small changes to later because it
            # is a lot faster to throw away as much of the template as possible
            # rather than performing lots of small shrinks.
            yield self._simplify_to_subtrees

            # Note that we try deleting leaves before we try simplifying them.
            # This is because it's likely to be a lot cheaper this way round,
            # as if we can delete a leaf we never have to try simplifying it.
            yield self._delete_leaves
            for i in range(self._template_size(template)):
                yield self._leaf_simplifier(i)
        else:
            assert len(template) == 1
            for s in self.leaf_strategy.simplifiers(random, template[0]):
                yield self._convert_leaf_simplifier(s)

    def _simplify_to_subtrees(self, random, template):
        """If this template corresponds to a Split, yield the templates for
        each subtree in a random order. Otherwise do nothing.

        This would be useful for e.g. tests that only care about the presence
        or absence of a particular leaf label in order to fail, and would allow
        us to simply extract that leaf.

        The randomness is not essential, but empirically it seems to work
        better to make random choices when one is presented to you because it
        makes you more robust against hitting pathological edge cases from
        certain structures.

        """
        if len(template) == 3:
            start = random.randint(0, 1)
            yield template[start]
            yield template[1 - start]

    def _convert_leaf_simplifier(self, simplifier):
        """This takes a single simplifier for leaf labels and turns it into a
        simplifier for trees that will only do something if the tree is a
        leaf."""

        def accept(random, template):
            if len(template) != 1:
                return

            for label in simplifier(random, template[0]):
                yield (label,)
        accept.__name__ = str(
            '_convert_leaf_simplifier(%s)' % (simplifier.__name__,)
        )
        return accept

    def _delete_leaf_at(self, index, template):
        """If this tree is a split with at least index leaves, return a
        template that is the same as this template with that leaf deleted,
        otherwise return the template unchanged."""
        assert index >= 0
        if len(template) != 3:
            return template
        if index >= self._template_size(template):
            return template
        left_size = self._template_size(template[0])
        right_size = self._template_size(template[1])

        if index < left_size:
            if left_size == 1:
                return template[1]
            else:
                return self._make_split(
                    self._delete_leaf_at(index, template[0]),
                    template[1]
                )
        else:
            if right_size == 1:
                return template[0]
            else:
                return self._make_split(
                    template[0],
                    self._delete_leaf_at(index - left_size, template[1])
                )

    def _delete_leaves(self, random, template):
        """Simplifier that tries to delete individual leaves one at a time."""
        if len(template) == 1:
            return
        for i in range(self._template_size(template)):
            yield self._delete_leaf_at(i, template)

    def _simplify_leaf_at(self, index, random, template):
        """Simplifier that applies a full simplify to each leaf. Note that
        unlike the behaviour when our top level template is a leaf we use
        full_simplify. This is to prevent a combinatorial explosion: If we
        were to use all the individual simplifiers of the leaves we would
        potentially have a very large numbeer of simplifiers to consider.

        All full_simplify does is run each simplifier (albeit in a slightly
        randomized order), so we still get the same amount of simplification.
        This does prevent certain optimisations in how simplify normally works.
        It's a trade-off - you have to strike a balance between number of
        simplifiers and quality of simplification. Usually the only way to
        find the right balance is trial and error.
        """
        assert index >= 0
        if index >= self._template_size(template):
            return
        if len(template) == 1:
            for simpler in self.leaf_strategy.full_simplify(
                random, template[0]
            ):
                yield (simpler,)
        else:
            assert len(template) == 3
            left = self._template_size(template[0])
            if index < left:
                for simpler in self._simplify_leaf_at(
                    index, random, template[0]
                ):
                    yield self._make_split(simpler, template[1])
            else:
                for simpler in self._simplify_leaf_at(
                    index - left, random, template[1]
                ):
                    yield self._make_split(template[0], simpler)

    def _leaf_simplifier(self, index):
        def accept(random, template):
            for result in self._simplify_leaf_at(index, random, template):
                yield result
        accept.__name__ = str(
            'leaf_simplifier(%d)' % (index,)
        )
        return accept

    def strictly_simpler(self, x, y):
        """This returns True in if x should be regarded as strictly simpler
        than y. This is a heuristic that is mainly used in collection
        simplification.

        - it allows us to e.g. simplify long lists by replacing more complex
        elements of the list with simpler ones and seeing if test still fails.

        It is not strictly necessary to implement this, but it will improve
        quality and performance when testing lists of values, so it's a good
        idea.

        """
        # We always consider leaves simpler than splits
        if len(x) < len(y):
            return True
        if len(x) > len(y):
            return False
        assert len(x) == len(y)
        if len(x) == 1:
            # For leaves we delegate to the leaf strategy
            return self.leaf_strategy.strictly_simpler(x[0], y[0])
        assert len(x) == 3

        # We now compare number of leaf nodes. A template with fewer nodes is
        # always strictly simpler. We do this to preserve the required
        # invariant that a simplifier cannot produce something such that the
        # original would be consider strictly simpler: Without this step,
        # passing to a subtree could result in a more complex element.

        # This is also why we cache the template size on the tuple: It's
        # important for strictly_simpler to be relatively cheap to perform,
        # and this would have to do the full size calculation at every split,
        # then would recursively do it during the lexicographical ordering,
        # which turns this comparison into an O(n^2) ones.

        x_size = self._template_size(x)
        y_size = self._template_size(y)

        if x_size < y_size:
            return True
        if x_size > y_size:
            return False

        # We then order lexicographically: That is, we first determine if the
        # left tree of either side is simpler than the other and use that, then
        # we look at the right tree.
        if self.strictly_simpler(x[0], y[0]):
            return True
        if self.strictly_simpler(y[0], x[0]):
            return False

        return self.strictly_simpler(x[1], y[1])

    # We now need to define serialization rules so that binary trees can be
    # saved in the database. This involves converting the elements to so called
    # basic data. Basic data is any of unicode, integers, bools, None, or lists
    # of other basic data.

    def to_basic(self, template):
        """We simply convert our templates to lists, but note that we must also
        use the defined to_basic for our leaves so that those are also
        correctly serialized."""
        if len(template) == 3:
            return [
                self.to_basic(template[0]), self.to_basic(template[1])
            ]
        else:
            assert len(template) == 1
            return [self.leaf_strategy.to_basic(template[0])]

    def from_basic(self, data):
        """
        from_basic simply undoes to_basic, but it must satisfy an important
        invariant: It either returns a valid template or it raises BadData.
        Any other exception is a bug in your implementation, as is returning a
        template that can't be used correctly.

        This is important because it maintains the invariant that you can use
        any Hypothesis database without worry about its age or whether the
        strategy implementation has changed since the examples were saved: The
        worst case scenario is that it won't help you, not that it will cause
        problems.
        """
        # check_data_type is a convenience function that raises BadData if the
        # data is not of the specified type.
        check_data_type(list, data)

        if len(data) == 1:
            return (self.leaf_strategy.from_basic(data[0]),)
        else:
            # Same deal: If the length is not 2, raise BadData.
            check_length(2, data)
            return self._make_split(*map(self.from_basic, data))


# Hypothesis convention is to wrap all strategy production into helper
# functions rather than expose strategy classes directly. This isn't strictly
# necessary in this case but is generally good practice.

def binary_trees(leaves):
    # The call to strategy is part of the deprecated strategy building API.
    # Until Hypothesis 2.0 this will work but will emit a warning (error in
    # strict mode) when called with a non-strategy argument.
    return BinaryTreeStrategy(strategy(leaves))

# We now want to test our implementation. Hypothesis provides a standard suite
# of tests you can run to check that your implementation is working correctly.
# We test two examples: One with empty labels, the other with integer labels.

TestBinaryTreeOfNone = strategy_test_suite(binary_trees(just(None)))
TestBinaryTreeOfInts = strategy_test_suite(binary_trees(integers()))


# If we've got to here we should now have a working strategy. Now lets look
# at some explicit examples to make sure that everything is simplifying well
# and we can find the examples we want to find.


# First we'll define some convenience functions that we'll need for delineating
# different areas of the search space and testing our results.

def labels(tree):
    """Convenience function for getting all labels out of a tree, no matter how
    deep they are."""
    if isinstance(tree, Leaf):
        yield tree.label
    else:
        for t in (tree.left, tree.right):
            for l in labels(t):
                yield l


def depth(tree):
    """We'll want to know the depth of various trees to test that we can reach
    certain regions."""
    if isinstance(tree, Leaf):
        return 1
    else:
        return 1 + max(depth(tree.left), depth(tree.right))


def size(tree):
    """Return the number of leaf nodes in a tree."""
    if isinstance(tree, Leaf):
        return 1
    else:
        return size(tree.left) + size(tree.right)


def test_simplifies_to_single_leaf():
    """The simplest possible tree should be a single leaf with the simplest
    possible label.

    If it's not we've done something very wrong

    """
    assert find(binary_trees(integers()), lambda x: True) == Leaf(0)


def test_simplifies_leaves_deep_in_the_tree():
    """Make sure that leaves are fully simplified even if they are deep in the
    tree rather than at the surface."""
    deep_tree = find(binary_trees(integers()), lambda x: depth(x) >= 5)
    for l in labels(deep_tree):
        assert l == 0


def test_simplifies_large_lists_of_trees_to_empty():
    """This uses the simplify_such_that heuristic.

    Simplifying individual elements of this list could take a very long
    time, but because we don't actually care about the elements we can
    use example cloning to skip over that process by just copying our
    current simplest example everywhere

    """
    forest = find(lists(binary_trees(integers())), lambda x: len(x) >= 50)
    assert forest == [Leaf(0)] * 50


def test_simplifies_list_of_trees_with_more_complex_structure():
    """This on the other hand is test for lists where we do care about the
    list."""
    forest = find(
        lists(binary_trees(just(None))), lambda x: sum(map(depth, x)) >= 50)
    assert sum(map(depth, forest)) == 50


def test_finds_a_large_tree():
    """Make sure that we are able to find large as well as small trees, and
    that we have no trouble simplifying down to that size boundary."""
    tree = find(binary_trees(just(None)), lambda x: size(x) >= 100)
    assert size(tree) == 100
