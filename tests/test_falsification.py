from hypothesis.verifier import (
    falsify,
    assume,
    Unfalsifiable,
    Unsatisfiable,
    Exhausted,
    Timeout,
    Flaky,
    Verifier,
)
import hypothesis.descriptors as descriptors
from hypothesis.internal.specmapper import MissingSpecification
from hypothesis.searchstrategy import (
    SearchStrategy,
)
from hypothesis.descriptors import one_of
from hypothesis.strategytable import (
    StrategyTable,
    strategy_for,
)
from collections import namedtuple
import pytest
import re
from hypothesis.internal.compat import hrange
import hypothesis.params as params
import hypothesis.settings as hs
import time
from hypothesis.internal.compat import binary_type, text_type
from random import Random


def test_can_make_assumptions():
    def is_good(x):
        assume(x > 5)
        return x % 2 == 0
    assert falsify(is_good, int)[0] == 7


class Foo(object):
    pass


class FooStrategy(SearchStrategy):
    descriptor = Foo
    parameter = params.CompositeParameter()

    def produce(self, random, pv):
        return Foo()


strategy_for(Foo)(FooStrategy())


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

    def __eq__(self, other):
        return isinstance(other, Bar) and self.size() == other.size()


class BarStrategy(SearchStrategy):
    descriptor = Bar

    def __init__(self, int_strategy):
        super(BarStrategy, self).__init__()
        self.int_strategy = int_strategy
        self.parameter = self.int_strategy.parameter

    def produce(self, random, pv):
        x = Bar()
        for _ in hrange(self.int_strategy.produce(random, pv)):
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
    strategies = StrategyTable()
    strategies.define_specification_for(
        Bar, lambda s, d: BarStrategy(
            s.strategy(descriptors.integers_in_range(0, 100))))

    with pytest.raises(MissingSpecification):
        StrategyTable.default().strategy(Bar)

    verifier = Verifier(strategy_table=strategies)
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
    def commutes(x, y):
        return x + y == y + x

    non_commuting = falsify(commutes, text_type, text_type)
    x, y = sorted(non_commuting)
    assert x == '0'
    assert y == '1'


def test_can_falsify_sets():
    assert falsify(lambda x: not x, {int})[0] == {0}


def test_can_falsify_list_inclusion():
    assert falsify(lambda x, y: x not in y, int, [int]) == (0, [0])


def test_can_falsify_set_inclusion():
    assert falsify(lambda x, y: x not in y, int, {int}) == (0, {0})


def test_can_falsify_lists():
    assert falsify(lambda x: len(x) < 3, [int])[0] == [0] * 3


def test_can_falsify_long_lists():
    long_list = falsify(lambda x: len(x) < 20, [int])[0]
    assert len(long_list) == 20


def test_can_find_unsorted_lists():
    unsorted = falsify(lambda x: sorted(x) == x, [int])[0]
    assert unsorted == [1, 0] or unsorted == [0, -1]


def is_pure(xs):
    return len(set([a.__class__ for a in xs])) <= 1


def test_can_falsify_mixed_lists():
    xs = falsify(is_pure, [int, text_type])[0]
    assert len(xs) == 2
    assert 0 in xs
    assert '' in xs


def test_can_produce_long_mixed_lists_with_only_a_subset():
    def short_or_includes(t):
        def is_good(xs):
            if len(xs) < 20:
                return True
            return any(isinstance(x, t) for x in xs)
        return is_good

    falsify(short_or_includes(text_type), [int, text_type])
    falsify(short_or_includes(int), [int, text_type])


def test_can_falsify_alternating_types():
    falsify(lambda x: isinstance(x, int), one_of([int, text_type]))[0] == ''


def test_can_falsify_string_matching():
    # Note that just doing a match("foo",x) will never find a good solution
    # because the state space is too large
    assert falsify(lambda x: not re.search('a.*b', x), text_type)[0] == 'ab'


def test_minimizes_strings_to_zeroes():
    assert falsify(lambda x: len(x) < 3, text_type)[0] == '000'


def test_can_find_short_strings():
    assert falsify(lambda x: len(x) > 0, text_type)[0] == ''
    assert len(falsify(lambda x: len(x) <= 1, text_type)[0]) == 2
    assert falsify(lambda x: len(x) < 10, [text_type])[0] == [''] * 10


def test_stops_loop_pretty_quickly():
    with pytest.raises(Unfalsifiable):
        falsify(lambda x: x == x, int)


def test_good_errors_on_bad_values():
    some_string = 'I am the very model of a modern major general'
    with pytest.raises(MissingSpecification) as e:
        falsify(lambda x: False, some_string)  # pragma: no branch

    assert some_string in e.value.args[0]


def test_can_falsify_bools():
    assert not falsify(lambda x: x, bool)[0]


def test_can_falsify_lists_of_bools():
    falsify(lambda x: len([y for y in x if not y]) <= 5, [bool])


def test_can_falsify_empty_tuples():
    assert falsify(lambda x: False, ())[0] == ()


Litter = namedtuple('Litter', ('kitten1', 'kitten2'))


def test_can_falsify_named_tuples():
    pair = falsify(
        lambda x: x.kitten1 < x.kitten2, Litter(text_type, text_type))[0]
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


def test_gravitates_towards_good_parameter_values():
    good_value_counts = [0]

    def just_being_awkward(xs):
        assume(len(xs) >= 50)
        assume(all(x >= 0 for x in xs))
        good_value_counts[0] += 1
        return True
    with pytest.raises(Unfalsifiable):
        falsify(
            just_being_awkward, [float]
        )

    assert good_value_counts[0] >= 100


def test_detects_flaky_failure():
    calls = [0]

    def flaky(x):
        result = calls != [0]
        calls[0] = 1
        return result

    with pytest.raises(Flaky):
        falsify(flaky, int)


def test_raises_timeout_on_timeout():
    # slow enough that it won't get a full set of examples but fast enough
    # that it will get at least min_satisfying_examples
    sleep_time = 0.001
    timeout = sleep_time * hs.default.min_satisfying_examples * 2

    def good_but_slow(x):
        time.sleep(sleep_time)
        return True
    verifier = Verifier(settings=hs.Settings(timeout=timeout))
    with pytest.raises(Timeout):
        verifier.falsify(good_but_slow, int)


def test_can_falsify_with_true_boolean():
    assert falsify(lambda x: not x, bool)[0] is True


def test_falsification_contains_function_string():
    with pytest.raises(Unfalsifiable) as e:
        assert falsify(lambda x: True, int)
    assert 'lambda x: True' in e.value.args[0]


def test_can_produce_and_minimize_long_lists_of_only_one_element():
    def is_a_monoculture(xs):
        assume(len(xs) >= 10)
        return len(set(xs)) > 1

    falsify(
        is_a_monoculture, [descriptors.integers_in_range(0, 10)])


def test_can_produce_things_that_are_not_utf8():
    def is_utf8(x):
        try:
            x.decode('utf-8')
            return True
        except UnicodeDecodeError:
            return False

    falsify(is_utf8, binary_type)


def test_can_produce_long_lists_with_floats_at_left():
    def is_small_given_large(xs):
        assume(len(xs) >= 15)
        return any(x >= 0.2 for x in xs)

    falsify(is_small_given_large, [descriptors.floats_in_range(0, 1)])


def test_can_produce_long_lists_with_floats_at_right():
    def is_small_given_large(xs):
        assume(len(xs) >= 15)
        return any(x <= 0.8 for x in xs)

    falsify(is_small_given_large, [descriptors.floats_in_range(0, 1)])


def test_does_not_call_twice_with_same_passing_parameter():
    calls = [0]

    def count_calls(x):
        calls[0] += 1
        return True
    with pytest.raises(Exhausted):
        falsify(count_calls, bool)
    assert calls == [2]


def test_works_with_zero_arguments():
    with pytest.raises(Unfalsifiable):
        falsify(lambda: True)
    falsify(lambda: False)


always_false = lambda *args: False


@pytest.mark.parametrize('desc', [
    int, float, complex, text_type, binary_type, bool
])
def test_minimizes_to_empty(desc):
    x = falsify(always_false, desc)[0]
    s = StrategyTable.default().strategy(desc)
    assert not list(s.simplify(x))


def test_falsifies_integer_keyed_dictionary():
    falsify(always_false, {1: int})


def test_falsifies_sets_of_union_types():
    assert falsify(always_false, {
        one_of([text_type, binary_type])})[0] == set()


def test_can_falsify_methods_which_mutate_data_without_proving_flaky():
    def pop_single(xs):
        if len(xs) == 1:
            xs.pop()
            return False
        return True

    assert falsify(pop_single, [int]) == ([0],)


def test_can_find_an_element_in_a_list():
    falsify(lambda x, ys: x not in ys, int, [int])


def test_can_randomize_random():
    falsify(lambda x: x.randint(0, 10) != 10, Random)


class BrokenFloatStrategy(SearchStrategy):
    descriptor = float
    parameter = params.CompositeParameter()

    def produce(self, random, pv):
        return random.random()


def test_two_verifiers_produce_different_results_in_normal_mode():
    table = StrategyTable()
    table.define_specification_for(float, lambda *_: BrokenFloatStrategy())
    v1 = Verifier(strategy_table=table)
    v2 = Verifier(strategy_table=table)
    x1 = v1.falsify(lambda x: False, float)
    x2 = v2.falsify(lambda x: False, float)
    assert x1 != x2


def test_two_verifiers_produce_the_same_results_in_derandomized_mode():
    table = StrategyTable()
    settings = hs.Settings(derandomize=True)
    table.define_specification_for(float, lambda *_: BrokenFloatStrategy())
    v1 = Verifier(strategy_table=table, settings=settings)
    v2 = Verifier(strategy_table=table, settings=settings)
    foo = lambda x: False

    x1 = v1.falsify(foo, float)
    x2 = v2.falsify(foo, float)
    assert x1 == x2


def test_a_derandomized_verifier_produces_the_same_results_called_twice():
    table = StrategyTable()
    settings = hs.Settings(derandomize=True)
    table.define_specification_for(float, lambda *_: BrokenFloatStrategy())
    v1 = Verifier(strategy_table=table, settings=settings)
    foo = lambda x: False
    x1 = v1.falsify(foo, float)
    x2 = v1.falsify(foo, float)
    assert x1 == x2


def test_minor_variations_in_code_change_the_randomization():
    table = StrategyTable()
    settings = hs.Settings(derandomize=True)
    table.define_specification_for(float, lambda *_: BrokenFloatStrategy())
    v1 = Verifier(strategy_table=table, settings=settings)
    x1 = v1.falsify(lambda x: x == 42, float)
    x2 = v1.falsify(lambda x: x == 1, float)
    assert x1 != x2


def test_can_derandomize_on_evalled_functions():
    table = StrategyTable()
    settings = hs.Settings(derandomize=True)
    v = Verifier(strategy_table=table, settings=settings)
    assert v.falsify(eval('lambda x: x > 0'), int) == (0,)
