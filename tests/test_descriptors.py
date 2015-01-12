import hypothesis.descriptors as descriptors
import pytest


def test_errors_on_empty_one_of():
    with pytest.raises(ValueError):
        descriptors.one_of([])


def test_returns_just_a_single_element():
    assert descriptors.one_of([1]) == 1
