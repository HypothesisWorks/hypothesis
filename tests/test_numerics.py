from hypothesis import given, assume
from fractions import Fraction
from tests.common.utils import fails
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
