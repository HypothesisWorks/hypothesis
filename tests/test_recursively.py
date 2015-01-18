from hypothesis.internal.compat import binary_type, text_type
from hypothesis.descriptors import (
    just, Just,
    OneOf
)
from hypothesis.internal.compat import hrange
import hypothesis.searchstrategy as strat
from hypothesis.searchstrategy import SearchStrategy, nice_string
from hypothesis.strategytable import StrategyTable
import hypothesis.params as params
from hypothesis.internal.utils.distributions import geometric, biased_coin
from hypothesis.testdecorators import given
from hypothesis import Verifier, Unfalsifiable, assume
import pytest
import re
import signal
import time
from functools import wraps
import hypothesis.settings as hs
from random import Random
from hypothesis.searchstrategy import RandomWithSeed

RandomWithSeed(0)  # Placate flake8


class Timeout(BaseException):
    pass


# The tests here have a tendency to run away with themselves a it if something
# goes wrong, so we use a relatively hard kill timeout.
def timeout(seconds=1):
    def decorate(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            start = time.time()

            def handler(signum, frame):
                raise Timeout('Timed out after %.2fs' % (time.time() - start))

            old_handler = signal.signal(signal.SIGALRM, handler)
            signal.alarm(seconds)
            try:
                return f(*args, **kwargs)
            finally:
                signal.signal(signal.SIGALRM, old_handler)
                signal.alarm(0)
        return wrapped
    return decorate


test_table = StrategyTable()

test_table.define_specification_for_instances(
    list,
    lambda strategies, descriptor:
        strat.ListStrategy(
            list(map(strategies.strategy, descriptor)),
            average_length=2.0
        )
)

primitive_types = [int, float, text_type, binary_type, bool, complex]
basic_types = list(primitive_types)
basic_types.append(OneOf(tuple(basic_types)))
basic_types += [frozenset({x}) for x in basic_types]
basic_types += [set({x}) for x in basic_types]
basic_types.append(Random)
branch_types = [dict, tuple, list]


class DescriptorStrategy(SearchStrategy):
    descriptor = object

    def __init__(self):
        self.key_strategy = test_table.strategy(
            OneOf((text_type, binary_type, int, bool))
        )
        self.parameter = params.CompositeParameter(
            leaf_descriptors=params.NonEmptySubset(basic_types),
            branch_descriptors=params.NonEmptySubset(branch_types),
            branch_factor=params.UniformFloatParameter(0.6, 0.99),
            key_parameter=self.key_strategy.parameter,
            just_probability=params.UniformFloatParameter(0, 0.45),
        )

    def produce(self, random, pv):
        n_children = geometric(random, pv.branch_factor)
        if not n_children:
            return random.choice(pv.leaf_descriptors)
        elif n_children == 1 and biased_coin(random, pv.just_probability):
            new_desc = self.produce(random, pv)
            child_strategy = test_table.strategy(new_desc)
            pv2 = child_strategy.parameter.draw(random)
            return just(child_strategy.produce(random, pv2))

        children = [self.produce(random, pv) for _ in hrange(n_children)]
        combiner = random.choice(pv.branch_descriptors)
        if combiner != dict:
            return combiner(children)
        else:
            result = {}
            for v in children:
                k = self.key_strategy.produce(random, pv.key_parameter)
                result[k] = v
            return result

    def simplify(self, value):
        if isinstance(value, dict):
            children = list(value.values())
        elif isinstance(value, Just):
            return
        elif isinstance(value, (list, set, tuple)):
            children = list(value)
        else:
            return
        for child in children:
            yield child

descriptor_strategy = DescriptorStrategy()


def size(descriptor):
    if descriptor in primitive_types:
        return 1
    elif isinstance(descriptor, dict):
        children = descriptor.values()
    elif isinstance(descriptor, Just):
        return 1
    else:
        try:
            children = list(descriptor)
        except TypeError:
            return 1
    return 1 + sum(map(size, children))


MAX_SIZE = 15
settings = hs.Settings(max_examples=100, timeout=4)

verifier = Verifier(
    settings=settings,
    strategy_table=test_table,
)


@given(descriptor_strategy, verifier=verifier)
@timeout(5)
def test_can_falsify_false_things(desc):
    assume(size(desc) <= MAX_SIZE)
    x = verifier.falsify(lambda x: False, desc)[0]
    strategy = test_table.strategy(desc)
    assert not list(strategy.simplify(x))


@given([descriptor_strategy], verifier=verifier)
@timeout(5)
def test_can_falsify_false_things_with_many_args(descs):
    assume(len(descs) > 0)
    assume(size(descs) <= MAX_SIZE)
    descs = tuple(descs)
    x = verifier.falsify(lambda *args: False, *descs)
    strategy = test_table.strategy(descs)
    assert not list(strategy.simplify(x))


@given(descriptor_strategy, verifier=verifier)
@timeout(5)
def test_can_not_falsify_true_things(desc):
    assume(size(desc) <= MAX_SIZE)
    with pytest.raises(Unfalsifiable):
        verifier.falsify(lambda x: True, desc)

UNDESIRABLE_STRINGS = re.compile('|'.join(
    re.escape(repr(t)) for t in primitive_types
))


@timeout(5)
@given(descriptor_strategy, verifier=verifier)
def test_does_not_use_nasty_type_reprs_in_nice_string(desc):
    s = nice_string(desc)
    assert not UNDESIRABLE_STRINGS.findall(s)
    read_desc = eval(s)
    assert desc == read_desc


def tree_contains_match(t, f):
    if f(t):
        return True
    if isinstance(t, (text_type, binary_type)):
        # Workaround for stupid one element string behaviour
        return False
    try:
        t = list(t)
    except TypeError:
        return False
    return any(tree_contains_match(s, f) for s in t)


def is_immutable_data(t):
    return not tree_contains_match(
        t, lambda x: isinstance(x, (list, set, dict)))


def test_basic_tree_matching():
    """Just an integrity check to make sure we're testing the right thing
    here."""

    assert not is_immutable_data([1])
    assert not is_immutable_data(([1],))
    assert not is_immutable_data({'foo': 1})
    assert is_immutable_data((1, 1))
    assert is_immutable_data('foo')


@timeout(5)
@given(descriptor_strategy, verifier=verifier)
def test_cannot_generate_mutable_data_from_an_immutable_strategy(d):
    strategy = test_table.strategy(d)
    assume(strategy.has_immutable_data)
    with pytest.raises(Unfalsifiable):
        print(
            nice_string(d),
            verifier.falsify(is_immutable_data, d))


@timeout(5)
@given(descriptor_strategy, Random, verifier=verifier)
def test_copies_all_its_values_correctly(desc, random):
    strategy = test_table.strategy(desc)
    value = strategy.produce(random, strategy.parameter.draw(random))
    assert value == strategy.copy(value)


@given(descriptor_strategy, verifier=verifier)
def test_can_produce_what_it_produces(desc):
    strategy = test_table.strategy(desc)
    with pytest.raises(Unfalsifiable):
        verifier.falsify(strategy.could_have_produced, desc)
