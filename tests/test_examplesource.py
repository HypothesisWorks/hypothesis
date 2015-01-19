from hypothesis.examplesource import ExampleSource
from hypothesis.strategytable import StrategyTable
import random
from hypothesis.internal.compat import hrange

N_EXAMPLES = 1000


def test_negative_is_not_too_far_off_mean():
    source = ExampleSource(
        random=random.Random(),
        strategy=StrategyTable.default().strategy(int),
        storage=None,
    )
    positive = 0
    i = 0
    for example in source:
        if example >= 0:
            positive += 1
        i += 1
        if i >= N_EXAMPLES:
            break
    assert 0.3 <= float(positive) / N_EXAMPLES <= 0.7


def test_marking_negative_avoids_similar_examples():
    source = ExampleSource(
        random=random.Random(),
        strategy=StrategyTable.default().strategy(int),
        storage=None,
    )
    positive = 0
    i = 0
    for example in source:
        if example >= 0:
            positive += 1
        else:
            source.mark_bad()
        i += 1
        if i >= N_EXAMPLES:
            break
    assert float(positive) / N_EXAMPLES >= 0.8


def test_can_grow_the_set_of_available_parameters_if_doing_badly():
    runs = 10
    number_grown = 0
    number_grown_large = 0
    for _ in hrange(runs):
        source = ExampleSource(
            random=random.Random(),
            strategy=StrategyTable.default().strategy(int),
            storage=None,
            min_parameters=1,
        )
        i = 0
        for example in source:
            if example < 0:
                source.mark_bad()
            i += 1
            if i >= 100:
                break
        if len(source.parameters) > 1:
            number_grown += 1
        if len(source.parameters) > 10:
            number_grown_large += 1

    assert number_grown == runs
    assert number_grown_large <= 0.5 * runs
