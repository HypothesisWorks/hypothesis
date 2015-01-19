from hypothesis.examplesource import ExampleSource
from hypothesis.strategytable import StrategyTable
import random

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
    assert float(positive) / N_EXAMPLES >= 0.7
