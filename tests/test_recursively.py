from hypothesis.internal.compat import binary_type, text_type
from hypothesis.descriptors import (
    Just, just, OneOf, SampledFrom
)
from hypothesis.searchstrategy import nice_string
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
from tests.common.descriptors import Descriptor, primitive_types
from tests.common import small_table

# Placate flake8
[OneOf, just, Just, RandomWithSeed, SampledFrom]


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


def size(descriptor):
    if descriptor in primitive_types:
        return 1
    elif isinstance(descriptor, dict):
        children = descriptor.values()
    elif isinstance(descriptor, (Just, SampledFrom)):
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
    strategy_table=small_table,
)


@given(Descriptor, verifier=verifier)
@timeout(5)
def test_can_falsify_false_things(desc):
    assume(size(desc) <= MAX_SIZE)
    x = verifier.falsify(lambda x: False, desc)[0]
    strategy = small_table.strategy(desc)
    assert not list(strategy.simplify(x))


@given([Descriptor], verifier=verifier)
@timeout(5)
def test_can_falsify_false_things_with_many_args(descs):
    assume(len(descs) > 0)
    assume(size(descs) <= MAX_SIZE)
    descs = tuple(descs)
    x = verifier.falsify(lambda *args: False, *descs)
    strategy = small_table.strategy(descs)
    assert not list(strategy.simplify(x))


@given(Descriptor, verifier=verifier)
@timeout(5)
def test_can_not_falsify_true_things(desc):
    assume(size(desc) <= MAX_SIZE)
    with pytest.raises(Unfalsifiable):
        verifier.falsify(lambda x: True, desc)

UNDESIRABLE_STRINGS = re.compile('|'.join(
    re.escape(repr(t)) for t in primitive_types
))


@timeout(5)
@given(Descriptor, verifier=verifier)
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
@given(Descriptor, verifier=verifier)
def test_cannot_generate_mutable_data_from_an_immutable_strategy(d):
    strategy = small_table.strategy(d)
    assume(strategy.has_immutable_data)
    with pytest.raises(Unfalsifiable):
        print(
            nice_string(d),
            verifier.falsify(is_immutable_data, d))


@timeout(5)
@given(Descriptor, Random, verifier=verifier)
def test_copies_all_its_values_correctly(desc, random):
    strategy = small_table.strategy(desc)
    value = strategy.produce(random, strategy.parameter.draw(random))
    assert value == strategy.copy(value)


@given(Descriptor, verifier=verifier)
def test_can_produce_what_it_produces(desc):
    strategy = small_table.strategy(desc)
    with pytest.raises(Unfalsifiable):
        verifier.falsify(strategy.could_have_produced, desc)
