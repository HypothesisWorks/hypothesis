import pytest
import hypothesis.internal.distributions as dist
import random


def test_non_empty_of_empty_errors():
    with pytest.raises(ValueError):
        dist.non_empty_subset(random, [])


def test_non_empty_of_one_always_returns_it():
    assert dist.non_empty_subset(random, [1]) == [1]
    assert dist.non_empty_subset(random, [2]) == [2]
