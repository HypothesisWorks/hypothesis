from hypothesis.verifier import (
    falsify,
    assume,
    Unfalsifiable,
    Unsatisfiable,
    Verifier
)
from hypothesis.internal.specmapper import MissingSpecification
from hypothesis.searchstrategy import (
    SearchStrategy,
    MappedSearchStrategy,
    one_of,
    SearchStrategies,
    strategy_for
)
from collections import namedtuple
import pytest
import re
from six.moves import xrange


def test_can_make_assumptions():
    def is_good(x):
        assume(x > 5)
        return x % 2 == 0
    assert falsify(is_good, int)[0] == 7


class Foo(object):
    pass


@strategy_for(Foo)
class FooStrategy(SearchStrategy):

    def produce(self, size, flags):
        return Foo()


def test_can_falsify_types_without_minimizers():
    assert isinstance(falsify(lambda x: False, Foo)[0], Foo)


class Bar(object):

    def __init__(self, bar=None):
        self.bar = bar

    def size(self):
        s = 0
        while self:
            self = self.bar
            s += 1
        return s

    def __repr__(self):
        return 'Bar(%s)' % self.size()

    def __eq__(self, other):
        return isinstance(other, Bar) and self.size() == other.size()


class BarStrategy(SearchStrategy):

    def __init__(self, strategies, descriptor):
        SearchStrategy.__init__(self, strategies, descriptor)
        self.int_strategy = strategies.strategy(int)

    def produce(self, size, flags):
        x = Bar()
        for _ in xrange(self.int_strategy.produce(size, flags)):
            x = Bar(x)
        return x

    def simplify(self, bar):
        while True:
            bar = bar.bar
            if bar:
                yield bar
            else:
                return


def test_can_falsify_types_without_default_productions():
    strategies = SearchStrategies()
    strategies.define_specification_for(Bar, BarStrategy)

    with pytest.raises(MissingSpecification):
        SearchStrategies.default().strategy(Bar)

    verifier = Verifier(search_strategies=strategies)
    assert verifier.falsify(lambda x: False, Bar,)[0] == Bar()
    assert verifier.falsify(lambda x: x.size() < 3, Bar)[0] == Bar(Bar(Bar()))


def test_can_falsify_tuples():
    def out_of_order_positive_tuple(x):
        a, b = x
        assume(a > 0 and b > 0)
        assert a >= b
        return True
    assert falsify(out_of_order_positive_tuple, (int, int))[0] == (1, 2)


def test_can_falsify_dicts():
    def is_good(x):
        assume('foo' in x)
        assume('bar' in x)
        return x['foo'] < x['bar']
    assert falsify(
        is_good, {
            'foo': int, 'bar': int})[0] == {
        'foo': 0, 'bar': 0}


def test_can_falsify_assertions():
    def is_good(x):
        assert x < 3
        return True
    assert falsify(is_good, int)[0] == 3


def test_can_falsify_floats():
    x, y, z = falsify(
        lambda x, y, z: (x + y) + z == x + (y + z), float, float, float)
    assert (x + y) + z != x + (y + z)


def test_can_falsify_ints():
    assert falsify(lambda x: x != 0, int)[0] == 0


def test_can_find_negative_ints():
    assert falsify(lambda x: x >= 0, int)[0] == -1


def test_can_find_negative_floats():
    assert falsify(lambda x: x > -1.0, float)[0] == -1.0


def test_can_falsify_int_pairs():
    assert falsify(lambda x, y: x > y, int, int) == (0, 0)


def test_can_falsify_string_commutativity():
    assert tuple(
        sorted(
            falsify(
                lambda x,
                y: x +
                y == y +
                x,
                str,
                str))) == (
        '0',
        '1')


def test_can_falsify_sets():
    assert falsify(lambda x: not x, {int})[0] == {0}


def test_can_falsify_list_inclusion():
    assert falsify(lambda x, y: x not in y, int, [int]) == (0, [0])


def test_can_falsify_set_inclusion():
    assert falsify(lambda x, y: x not in y, int, {int}) == (0, {0})


def test_can_falsify_lists():
    assert falsify(lambda x: len(x) < 3, [int])[0] == [0] * 3


def test_can_falsify_long_lists():
    assert falsify(
        lambda x: len(x) < 20,
        [int],
        warming_rate=0.5)[0] == [0] * 20


def test_can_find_unsorted_lists():
    unsorted = falsify(lambda x: sorted(x) == x, [int])[0]
    assert unsorted == [1, 0] or unsorted == [0, -1]


def is_pure(xs):
    return len(set([a.__class__ for a in xs])) <= 1


def test_can_falsify_mixed_lists():
    xs = falsify(is_pure, [int, str])[0]
    assert len(xs) == 2
    assert 0 in xs
    assert '' in xs


def test_can_produce_long_mixed_lists_with_only_a_subset():
    def is_good(xs):
        if len(xs) < 20:
            return True
        if any((isinstance(x, int) for x in xs)):
            return True
        return False

    falsify(is_good, [int, str])


def test_can_falsify_alternating_types():
    falsify(lambda x: isinstance(x, int), one_of([int, str]))[0] == ''


class HeavilyBranchingTree(object):

    def __init__(self, children):
        self.children = children

    def depth(self):
        if not self.children:
            return 1
        else:
            return 1 + max(map(HeavilyBranchingTree.depth, self.children))


@strategy_for(HeavilyBranchingTree)
class HeavilyBranchingTreeStrategy(MappedSearchStrategy):

    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.mapped_strategy = strategies.strategy([HeavilyBranchingTree])

    def pack(self, x):
        return HeavilyBranchingTree(x)

    def unpack(self, x):
        return x.children


def test_can_go_deep_into_recursive_strategies():
    falsify(lambda x: x.depth() <= 5, HeavilyBranchingTree)


def test_can_falsify_string_matching():
    # Note that just doing a match("foo",x) will never find a good solution
    # because the state space is too large
    assert falsify(lambda x: not re.search('a.*b', x), str)[0] == 'ab'


def test_minimizes_strings_to_zeroes():
    assert falsify(lambda x: len(x) < 3, str)[0] == '000'


def test_can_find_short_strings():
    assert falsify(lambda x: len(x) > 0, str)[0] == ''
    assert len(falsify(lambda x: len(x) <= 1, str)[0]) == 2
    assert falsify(lambda x: len(x) < 10, [str])[0] == [''] * 10


def test_stops_loop_pretty_quickly():
    with pytest.raises(Unfalsifiable):
        falsify(lambda x: x == x, int)


def test_good_errors_on_bad_values():
    some_string = 'I am the very model of a modern major general'
    with pytest.raises(MissingSpecification) as e:
        falsify(lambda x: False, some_string)

    assert some_string in e.value.args[0]


def test_can_falsify_bools():
    assert not falsify(lambda x: x, bool)[0]


def test_can_falsify_lists_of_bools():
    falsify(lambda x: len([y for y in x if not y]) <= 5, [bool])


def test_can_falsify_empty_tuples():
    assert falsify(lambda x: False, ())[0] == ()


class BinaryTree(object):
    pass


class Leaf(BinaryTree):

    def __init__(self, label):
        self.label = label

    def depth(self):
        return 0

    def breadth(self):
        return 1

    def __eq__(self, that):
        return isinstance(that, Leaf) and self.label == that.label

    def __hash__(self):
        return hash(self.label)


class Split(BinaryTree):

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def depth(self):
        return 1 + max(self.left.depth(), self.right.depth())

    def breadth(self):
        return self.left.breadth() + self.right.breadth()

    def __eq__(self, that):
        return (
            isinstance(that, Split) and
            that.left == self.left and
            that.right == self.right
        )

    def __hash__(self):
        return hash(self.left) ^ hash(self.right)


@strategy_for(Leaf)
class LeafStrategy(MappedSearchStrategy):

    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.mapped_strategy = strategies.strategy(int)

    def pack(self, x):
        return Leaf(x)

    def unpack(self, x):
        return x.label


@strategy_for(Split)
class SplitStrategy(MappedSearchStrategy):

    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.mapped_strategy = strategies.strategy((BinaryTree, BinaryTree))

    def pack(self, x):
        return Split(*x)

    def unpack(self, x):
        return (x.left, x.right)


@strategy_for(BinaryTree)
class BinaryTreeStrategy(MappedSearchStrategy):

    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.mapped_strategy = strategies.strategy(one_of([Leaf, Split]))

    def child_strategies(self):
        return ()

    def pack(self, x):
        return x

    def unpack(self, x):
        return x


def test_can_produce_deep_binary_trees():
    falsify(lambda x: x.depth() <= 2, BinaryTree)

Litter = namedtuple('Litter', ('kitten1', 'kitten2'))


def test_can_falsify_named_tuples():
    pair = falsify(lambda x: x.kitten1 < x.kitten2, Litter(str, str))[0]
    assert isinstance(pair, Litter)
    assert pair == Litter('', '')


def test_can_falsify_complex_numbers():
    falsify(lambda x: x == (x ** 2) ** 0.5, complex)

    with pytest.raises(Unfalsifiable):
        falsify(
            lambda x, y: (
                x * y
            ).conjugate() == x.conjugate() * y.conjugate(), complex, complex)


def test_raises_on_unsatisfiable_assumption():
    with pytest.raises(Unsatisfiable):
        falsify(lambda x: assume(False), int)
