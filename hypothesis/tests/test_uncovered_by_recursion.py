"""
This is mostly just for things that I've found in the course of recursive
testing that don't obviously go somewhere else.
"""
from hypothesis import falsify

always_false = lambda *args: False


def test_falsifies_integer_keyed_dictionary():
    falsify(always_false, {1: int})
