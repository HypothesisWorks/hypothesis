"""
This is mostly just for things that I've found in the course of recursive
testing that don't obviously go somewhere else.
"""
from hypothesis import falsify
from hypothesis.descriptors import one_of
from six import text_type, binary_type

always_false = lambda *args: False


def test_falsifies_integer_keyed_dictionary():
    falsify(always_false, {1: int})


def test_falsifies_sets_of_union_types():
    falsify(always_false, {
        one_of([text_type, binary_type])})
