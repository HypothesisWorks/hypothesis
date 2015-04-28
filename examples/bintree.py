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

from collections import namedtuple
from hypothesis.searchstrategy import SearchStrategy
import math

from hypothesis.searchstrategy.strategies import check_length, check_data_type
from hypothesis.strategytests import strategy_test_suite
from hypothesis import strategy, find


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

    def produce_parameter(self, random):
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
            # too. Note that we call draw_parameter rather than
            # produce_parameter. produce_parameter is the implementation, but
            # draw_parameter wraps it as the API you're supposed to interact
            # with.
            leaf_parameter=self.leaf_strategy.draw_parameter(random)
        )

    def produce_template(self, context, parameter_value):
        """We now produce a template, which is a value that we will later turn
        into a binary tree.

        There are a number of reasons for the distinction which we won't
        go into here, but think of a template as an easier to work with
        intermediate representation of the final value. In particular
        templates are always hashable and comparable for equality, even
        if the finished product is not.

        """

        # Context is mostly a wrapper object for a random. This is the only
        # feature we will care about here.
        random = context.random

        # Our templates will be tuples of 1 or 2 elements. A tuple of 1 element
        # is a leaf and will contain a leaf template, a tuple of 2 elements is
        # a split and will contain two BinaryTree templates.

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

        # We now draw templates for each leaf. Note that again there is the
        # draw_template / produce_template distinction.
        leaf_templates = tuple(
            self.leaf_strategy.draw_template(
                context, parameter_value.leaf_parameter)
            for _ in range(n_leaf_labels)
        )

        # We now need to need to figure out how to distribute the leaves.
        # We do this recursively, so farm off to another method.
        return self.split_leaf_list(
            leaf_templates, random, parameter_value.split_location
        )

    def split_leaf_list(self, leaves, random, split_location):
        # Calling this on an empty list is a logical error.
        assert leaves

        if len(leaves) == 1:
            # If we have only one leaf then this is already the template for
            # a single node and we're done.
            return leaves
        if len(leaves) == 2:
            # If we only have two, this can only be produced as a single split
            # with a leaf on either side.
            return tuple(
                (x,) for x in leaves
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

        # We now have two nice little piles of nodes to put on the left and
        # the right side of this split, and we must split those too.
        return (
            self.split_leaf_list(tuple(left), random, split_location),
            self.split_leaf_list(tuple(right), random, split_location),
        )

    def reify(self, template):
        """Reify is the point at which we take our templates and turn them into
        the values we actually want.

        Our templates here quite closely map to the desired end type, so
        all we have to do is make sure to reify the leaves and then
        assemble the templates into the appropriate BinaryTree subtype.

        """
        assert 1 <= len(template) <= 2
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
        if len(template) == 2:
            yield self.simplify_to_subtrees
            # We try the subtrees in a random order because this generallly
            # seems to help. It's not really necessary, but it's often useful
            # and is easy to do so we might as well.
            start = random.randint(0, 1)
            yield self.simplify_single_subtree(start)
            yield self.simplify_single_subtree(1 - start)
        else:
            assert len(template) == 1
            for s in self.leaf_strategy.simplifiers(random, template[0]):
                yield self.convert_leaf_simplifier(s)

    def simplify_to_subtrees(self, random, template):
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
        if len(template) == 2:
            start = random.randint(0, 1)
            yield template[start]
            yield template[1 - start]

    def simplify_single_subtree(self, index):
        """Defines a simplifier that simplifies a single subtree of a split.

        This
        can be useful when you're testing things that look e.g. like having a
        very deep left subtree: It means that you can happily simplify the
        right hand side without bothering to keep trying to shrink the left.

        """
        def accept(random, template):
            if len(template) != 2:
                return

            # full_simplify tries all the simplifiers available for a template
            # on it, not necessarily in the specified order. The reason we use
            # this rather than using each simplifier for a template in turn is
            # that that would cause a combinatorial explosion, where a single
            # template could potentially have a vast number of simplifiers.
            # By using full_simplify at each level we can collapse that.
            for simpler in self.full_simplify(random, template[index]):
                result = list(template)
                result[index] = simpler
                yield tuple(result)
        # Assigning the name of a simplifier is not strictly necessary but it
        # helps for debugging
        accept.__name__ = str('simplify_single_subtree(%d)' % (index,))
        return accept

    def convert_leaf_simplifier(self, simplifier):
        """This takes a single simplifier for leaf labels and turns it into a
        simplifier for trees that will only do something if the tree is a
        leaf."""

        def accept(random, template):
            if len(template) != 1:
                return

            for label in simplifier(random, template[0]):
                yield (label,)
        accept.__name__ = str(
            'convert_leaf_simplifier(%s)' % (simplifier.__name__,)
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
        assert len(x) == 2

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
        if len(template) == 2:
            return list(map(self.to_basic, template))
        else:
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
            return tuple(map(self.from_basic, data))


# We can now explicitly construct instances of our strategy, but we wish to
# hook it into the strategy definition mechanism.
# If our BinaryTree did not have a particular type of leaf node we could just
# define how to convert the BinaryTree type into a strategy, but because it
# does we need more data to build one and need to define a custom specifier.

# These don't have to be namedtuples but they're convenient so they usually are
BinaryTrees = namedtuple('BinaryTrees', ('leaves',))


# strategy.extend(BinaryTrees) lets us provide an implementation for what will
# happen when we call strategy(spec, settings) with spec an instance of
# BinaryTrees.
@strategy.extend(BinaryTrees)
def binary_trees_strategy(spec, settings):
    """Build a binary tree strategy by building a strategy for the leaf type
    and then constructing the strategy we defined above."""
    return BinaryTreeStrategy(strategy(spec.leaves, settings))


# We now want to test our implementation. Hypothesis provides a standard suite
# of tests you can run to check that your implementation is working correctly.
# We test two examples: One with empty labels, the other with integer labels.

TestBinaryTreeOfNone = strategy_test_suite(BinaryTrees(None))
TestBinaryTreeOfInts = strategy_test_suite(BinaryTrees(int))


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
    assert find(BinaryTrees(int), lambda x: True) == Leaf(0)


def test_simplifies_leaves_deep_in_the_tree():
    """Make sure that leaves are fully simplified even if they are deep in the
    tree rather than at the surface."""
    deep_tree = find(BinaryTrees(int), lambda x: depth(x) >= 5)
    for l in labels(deep_tree):
        assert l == 0


def test_simplifies_large_lists_of_trees_to_empty():
    """This uses the simplify_such_that heuristic.

    Simplifying individual elements of this list could take a very long
    time, but because we don't actually care about the elements we can
    use example cloning to skip over that process by just copying our
    current simplest example everywhere

    """
    forest = find([BinaryTrees(int)], lambda x: len(x) >= 50)
    assert forest == [Leaf(0)] * 50


def test_simplifies_list_of_trees_with_more_complex_structure():
    """This on the other hand is test for lists where we do care about the
    list."""
    forest = find([BinaryTrees(None)], lambda x: sum(map(depth, x)) >= 50)
    assert sum(map(depth, forest)) == 50


def test_finds_a_large_tree():
    """Make sure that we are able to find large as well as small trees, and
    that we have no trouble simplifying down to that size boundary."""
    tree = find(BinaryTrees(None), lambda x: size(x) >= 100)
    assert size(tree) == 100
