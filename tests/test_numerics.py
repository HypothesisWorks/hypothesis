from hypothesis import given, assume
from fractions import Fraction
from tests.common.utils import fails, simplest_example_satisfying
from decimal import Decimal


@fails
@given(Decimal)
def test_all_decimals_can_be_exact_floats(x):
    assume(x.is_finite())
    assert Decimal(float(x)) == x


@fails
@given([Decimal])
def test_reversing_preserves_decimal_addition(xs):
    assert sum(xs) == sum(reversed(xs))


@given([Fraction])
def test_reversing_preserves_fraction_addition(xs):
    assert sum(xs) == sum(reversed(xs))


def test_produces_reasonable_examples():
    assert simplest_example_satisfying(Decimal, lambda x: x >= 1) == Decimal(1)
    assert simplest_example_satisfying(
        Fraction, lambda x: x >= 1) == Fraction(1)
    assert simplest_example_satisfying(
        {Fraction}, lambda x: len(x) >= 3
    ) == {Fraction(0), Fraction(1), Fraction(2)}

    assert simplest_example_satisfying(
        Fraction, lambda x: x != int(x)
    ) == Fraction(1, 2)
