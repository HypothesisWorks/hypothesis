import hypothesis.strategytable as ss
import hypothesis.searchstrategy as strat
import hypothesis.descriptors as descriptors
from hypothesis.internal.tracker import Tracker
from collections import namedtuple
from six.moves import xrange
import random
import pytest


def strategy(*args, **kwargs):
    return ss.StrategyTable().strategy(*args, **kwargs)


def test_string_strategy_produces_strings():
    strings = strategy(str)
    result = strings.produce(random, strings.parameter.draw(random))
    assert result is not None


def test_tuples_inspect_component_types_for_production():
    strxint = strategy((str, int))

    assert strxint.could_have_produced(('', 2))
    assert not strxint.could_have_produced((2, 2))

    intxint = strategy((int, int))

    assert not intxint.could_have_produced(('', 2))
    assert intxint.could_have_produced((2, 2))


def alternating(*args):
    return strategy(descriptors.one_of(args))


def minimize(s, x):
    for t in s.simplify_such_that(x, lambda _: True):
        x = t
    return x


def test_can_minimize_component_types():
    ios = alternating(str, int)
    assert 0 == minimize(ios, 10)
    assert '' == minimize(ios, 'I like kittens')


def test_can_minimize_nested_component_types():
    ios = alternating((int, str), (int, int))
    assert (0, '') == minimize(ios, (42, 'I like kittens'))
    assert (0, 0) == minimize(ios, (42, 666))


def test_can_minimize_tuples():
    ts = strategy((int, int, int))
    assert minimize(ts, (10, 10, 10)) == (0, 0, 0)


def assert_no_duplicates_in_simplify(s, x):
    s = strategy(s)
    t = Tracker()
    t.track(x)
    for y in s.simplify(x):
        assert t.track(y) == 1


def test_ints_no_duplicates_in_simplify():
    assert_no_duplicates_in_simplify(int, 555)


def test_int_lists_no_duplicates_in_simplify():
    assert_no_duplicates_in_simplify([int], [0, 555, 1281])


def test_float_lists_no_duplicates_in_simplify():
    assert_no_duplicates_in_simplify(
        [float], [
            0.5154278802175156, 555.0, 1281.8556018727038])


def test_just_works():
    s = strategy(descriptors.just('giving'))
    assert s.produce(random, s.parameter.draw(random)) == 'giving'
    assert list(s.simplify_such_that('giving', lambda _: True)) == ['giving']


Litter = namedtuple('Litter', ('kitten1', 'kitten2'))


def test_named_tuples_always_produce_named_tuples():
    s = strategy(Litter(int, int))

    for i in xrange(100):
        assert isinstance(s.produce(random, s.parameter.draw(random)), Litter)

    for x in s.simplify(Litter(100, 100)):
        assert isinstance(x, Litter)


def test_strategy_repr_handles_dicts():
    s = repr(strategy({'foo': int, 'bar': str}))
    assert 'foo' in s
    assert 'bar' in s
    assert 'int' in s
    assert 'str' in s


def test_strategy_repr_handles_tuples():
    s = repr(strategy((str, str)))
    assert '(str, str)' in s


def test_strategy_repr_handles_bools():
    s = repr(strategy(bool))
    assert '(bool)' in s


class X(object):

    def __init__(self, x):
        self.x = x

    def __repr__(self):
        return 'X(%s)' % str(self.x)


@ss.strategy_for_instances(X)
class XStrategy(strat.MappedSearchStrategy):
    def pack(self, x):
        return X(x)

    def unpack(self, x):
        return x.x


@ss.strategy_for_instances(X)
def define_x_strategy(strategies, descriptor):
    return XStrategy(
        strategy=strategies.strategy(descriptor.x),
        descriptor=descriptor,
    )


def test_strategy_repr_handles_custom_types():
    assert 'X(x=str)' in repr(ss.StrategyTable().strategy(X(str)))


class TrivialStrategy(strat.SearchStrategy):
    def __init__(self, descriptor):
        self.descriptor = descriptor

    def produce(self, random, pv):
        return 0


def test_strategy_repr_handles_instances_without_dicts():
    strats = ss.StrategyTable()
    strats.define_specification_for_instances(
        int, lambda s, d: TrivialStrategy(d))

    assert repr(strats.strategy(42)) == 'TrivialStrategy(42)'
    assert repr(strats.strategy(23)) == 'TrivialStrategy(23)'


def test_float_strategy_does_not_overflow():
    strategy = ss.StrategyTable().strategy(float)

    for _ in xrange(100):
        strategy.produce(random, strategy.parameter.draw(random))


def test_does_not_shrink_tuple_length():
    bools = ss.StrategyTable().strategy((bool,))
    t = minimize(bools, (False,))
    assert len(t) == 1


def test_or_does_not_change_descriptor_given_single_descriptor():
    bools = ss.StrategyTable().strategy((bool,))
    b = bools | bools
    assert b.descriptor == bools.descriptor


def test_or_errors_when_given_non_strategy():
    bools = ss.StrategyTable().strategy((bool,))
    with pytest.raises(ValueError):
        bools | "foo"
