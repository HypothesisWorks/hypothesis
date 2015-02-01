"""
Tests for specific string representations of values
"""

from hypothesis.searchstrategy import nice_string


def test_nice_string_for_nasty_floats():
    assert nice_string(float('inf')) == "float('inf')"
    assert nice_string(float('-inf')) == "float('-inf')"
    assert nice_string(float('nan')) == "float('nan')"


def test_nice_string_for_nice_complex():
    assert nice_string(1+1j) == "(1+1j)"


def test_nice_string_for_nasty_complex():
    assert nice_string(
        complex(float('inf'), 0.0)) == "complex('inf+0j')"
