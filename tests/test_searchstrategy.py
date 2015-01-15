import hypothesis.strategytable as ss
import hypothesis.searchstrategy as strat
import hypothesis.descriptors as descriptors
import hypothesis.params as params
from hypothesis.internal.tracker import Tracker
from collections import namedtuple
from six.moves import xrange
from six import text_type, binary_type
import random
import pytest


def strategy(*args, **kwargs):
    return ss.StrategyTable().strategy(*args, **kwargs)


def test_string_strategy_produces_strings():
    strings = strategy(str)
    result = strings.produce(random, strings.parameter.draw(random))
    assert result is not None


def test_unary_tuple_strategy_has_trailing_comma():
    assert repr(strategy((str,))) == "TupleStrategy((str,))"


Blah = namedtuple('Blah', ('hi',))


def test_named_tuple_strategy_has_tuple_in_name_and_no_trailing_comma():
    assert repr(strategy(Blah(str))) == "TupleStrategy(Blah(hi=str))"


def test_class_names_are_simplified_in_sets():
    assert repr(strategy({float})) == "SetStrategy({float})"


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
    simplifications = list(s.simplify_such_that('giving', lambda _: True))
    assert len(simplifications) == 1
    assert simplifications[0] == 'giving'


Litter = namedtuple('Litter', ('kitten1', 'kitten2'))


def test_named_tuples_always_produce_named_tuples():
    s = strategy(Litter(int, int))

    for i in xrange(100):
        assert isinstance(s.produce(random, s.parameter.draw(random)), Litter)

    for x in s.simplify(Litter(100, 100)):
        assert isinstance(x, Litter)


def test_simplifying_something_that_does_not_satisfy_errors():
    s = strategy(int)
    f = lambda x: x > 100
    with pytest.raises(ValueError):
        next(s.simplify_such_that(1, f))


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


@ss.strategy_for_instances(X)
class XStrategy(strat.MappedSearchStrategy):
    pass


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


def test_joining_zero_strategies_fails():
    with pytest.raises(ValueError):
        strat.one_of_strategies(())


def test_directly_joining_one_strategy_also_fails():
    with pytest.raises(ValueError):
        strat.OneOfStrategy([strat.RandomGeometricIntStrategy()])


def test_list_strategy_reprs_as_list():
    x = ss.StrategyTable.default().strategy([int])
    assert repr(x) == "ListStrategy([int])"


def test_can_distinguish_amongst_tuples_of_mixed_length():
    st = ss.StrategyTable()
    mixed_strategy = st.strategy((int, int, int)) | st.strategy((int, int))
    assert mixed_strategy.could_have_produced((1, 1))
    assert mixed_strategy.could_have_produced((1, 1, 1))
    assert not mixed_strategy.could_have_produced((1, 1, 1, 1))
    assert not mixed_strategy.could_have_produced((1, "foo"))
    assert not mixed_strategy.could_have_produced((1, 1, "foo"))
    assert not mixed_strategy.could_have_produced([1, 1])


def test_one_char_string_strategy_must_be_given_chars():
    with pytest.raises(ValueError):
        strat.OneCharStringStrategy([1, 2, 3])


SomeNamedTuple = namedtuple('SomeNamedTuple', ('a', 'b'))


def test_distinguishes_named_and_unnamed_tuples():
    table = ss.StrategyTable()
    named = table.strategy(SomeNamedTuple(int, int))
    unnamed = table.strategy((int, int))

    assert unnamed.could_have_produced((1, 1))
    assert not named.could_have_produced((1, 1))

    assert not unnamed.could_have_produced(SomeNamedTuple(1, 1))
    assert named.could_have_produced(SomeNamedTuple(1, 1))

    for x in named.simplify(SomeNamedTuple(1, 1)):
        assert type(x) == SomeNamedTuple

    for x in unnamed.simplify((1, 1)):
        assert type(x) == tuple


class IntStrategyWithBrokenSimplify(strat.RandomGeometricIntStrategy):
    def simplify(self, value):
        return ()


def test_can_use_simplify_from_all_children():
    always = lambda x: True
    table = ss.StrategyTable()
    bad_strategy = IntStrategyWithBrokenSimplify()
    assert list(bad_strategy.simplify_such_that(42, always)) == [42]
    hybrid_strategy = bad_strategy | table.strategy(int)
    assert list(
        hybrid_strategy.simplify_such_that(42, always))[-1] == 0


def test_strategy_for_integer_range_produces_only_integers_in_that_range():
    table = ss.StrategyTable()
    just_one_integer = table.strategy(descriptors.IntegerRange(1, 1))
    for _ in xrange(100):
        pv = just_one_integer.parameter.draw(random)
        x = just_one_integer.produce(random, pv)
        assert x == 1
    some_integers = table.strategy(descriptors.IntegerRange(1, 10))
    for _ in xrange(100):
        pv = some_integers.parameter.draw(random)
        x = some_integers.produce(random, pv)
        assert 1 <= x <= 10


def test_strategy_for_integer_range_can_produce_end_points():
    table = ss.StrategyTable()
    some_integers = table.strategy(descriptors.IntegerRange(1, 10))
    found = set()
    for _ in xrange(1000):  # pragma: no branch
        pv = some_integers.parameter.draw(random)
        x = some_integers.produce(random, pv)
        found.add(x)
        if 1 in found and 10 in found:
            break
    else:
        assert False  # pragma: no cover
    assert 1 in found
    assert 10 in found


def last(xs):
    t = None
    for x in xs:
        t = x
    return t


def test_simplify_integer_range_can_push_to_near_boundaries():
    table = ss.StrategyTable()
    some_integers = table.strategy(descriptors.IntegerRange(1, 10))

    predicates = [
        (lambda x: True, 1),
        (lambda x: x > 1, 2),
        (lambda x: x > 5, 10),
        (lambda x: x > 5 and x < 10, 9),
    ]

    for p, v in predicates:
        some = False
        for i in xrange(1, 10):
            if p(i):
                some = True
                assert last(some_integers.simplify_such_that(i, p)) == v
        assert some


def test_rejects_invalid_ranges():
    with pytest.raises(ValueError):
        strat.BoundedIntStrategy(10, 9)


def test_does_not_simplify_outside_range():
    n = 3
    s = strat.BoundedIntStrategy(0, n)
    for t in s.simplify(n):
        assert 0 <= t <= n


def test_can_simplify_large_ints():
    ints = ss.StrategyTable().strategy(int)
    x = 2 ** 63
    assert ints.could_have_produced(x)
    assert minimize(ints, x) == 0
    assert minimize(ints, 100000) == 0


def test_can_simplify_dicts_of_ints():
    ints = ss.StrategyTable().strategy({'a': int, 'b': int})
    assert minimize(ints, {'a': 100000000000000, 'b': 2}) == {'a': 0, 'b': 0}


def test_can_simplify_imaginary_component():
    cs = ss.StrategyTable().strategy(complex)
    t = complex(1.0, 10.0)
    for s in cs.simplify_such_that(t, lambda x: x.real >= 0 and x.imag >= 1):
        t = s
    assert t.imag == 1.0


def test_can_simplify_real_component():
    cs = ss.StrategyTable().strategy(complex)
    t = complex(10.0, 1.0)
    for s in cs.simplify_such_that(t, lambda x: x.real >= 1 and x.imag >= 0):
        t = s
    assert t.real == 1.0


basic_types = [int, float, text_type, binary_type, complex, bool]
mutable_collection_types = [set, list]


@pytest.mark.parametrize('t', basic_types)
def test_is_immutable_given_basic_types(t):
    assert strategy(t).has_immutable_data


def test_frozen_set_of_immutable_types_is_immutable():
    assert strategy(frozenset([int])).has_immutable_data


def test_frozen_set_of_mutable_types_is_mutable():
    class Foo(object):
        pass

    class FooStrategy(strat.SearchStrategy):
        descriptor = Foo
        parameter = params.CompositeParameter()
        has_immutable_data = False

        def produce(self, random, pv):
            return Foo()

    table = ss.StrategyTable()
    table.define_specification_for(Foo, lambda s, d: FooStrategy())
    assert not table.strategy(frozenset([Foo])).has_immutable_data


@pytest.mark.parametrize('c', [
    c([t])
    for c in mutable_collection_types
    for t in basic_types
])
def test_mutable_collection_types_have_mutable_data(c):
    assert not strategy(c).has_immutable_data


def test_dicts_are_mutable():
    assert not strategy({1: int}).has_immutable_data


def test_tuples_with_one_mutable_arg_are_mutable():
    assert not strategy((int, [int])).has_immutable_data
    assert not strategy(([int], str)).has_immutable_data


def test_lists_of_tuples_are_mutable():
    assert not strategy([(int, int)]).has_immutable_data


def test_one_of_immutable_is_immutable():
    assert strategy(descriptors.one_of(
        [int, str, float, complex])).has_immutable_data


def test_one_of_mutable_is_mutable():
    assert not strategy(descriptors.one_of(
        [[int], [float]])).has_immutable_data


def test_one_of_mutable_and_immutable_is_mutable():
    assert not strategy(
        descriptors.one_of([int, [float]])).has_immutable_data


def test_random_is_mutable():
    assert not strategy(random.Random).has_immutable_data


def test_random_repr_has_seed():
    rnd = strategy(random.Random).produce(random.Random(), None)
    seed = rnd.seed
    assert str(seed) in repr(rnd)


def test_random_only_produces_special_random():
    strat = strategy(random.Random)
    assert not strat.could_have_produced(random.Random())
    assert strat.could_have_produced(
        strat.produce(random, strat.parameter.draw(random)))


def test_randoms_with_same_seed_and_state_are_equal():
    s = strat.RandomWithSeed(123)
    t = strat.RandomWithSeed(123)
    assert s == t
    s.random()
    assert s != t
    t.random()
    assert s == t


def test_nice_string_for_sets_is_not_a_dict():
    assert strat.nice_string(set()) == repr(set())
    assert strat.nice_string(frozenset()) == repr(frozenset())


def test_just_strategy_uses_repr():
    class WeirdRepr(object):
        def __repr__(self):
            return "ABCDEFG"

    assert repr(
        strategy(descriptors.just(WeirdRepr()))
    ) == "JustStrategy(value=%r)" % (WeirdRepr(),)


def test_just_nice_string_should_respect_its_values_reprs():
    class Stuff(object):
        def __repr__(self):
            return "Things()"
    assert strat.nice_string(
        descriptors.Just(Stuff())
    ) == "Just(value=Things())"
