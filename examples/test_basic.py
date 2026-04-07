# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import given, strategies as st


# Our tested class
class Product:
    def __init__(self, price: float) -> None:
        self.price: float = price

    def get_discount_price(self, discount_percentage: float):
        return self.price * (discount_percentage / 100)


# The @given decorator generates examples for us!
@given(
    price=st.floats(min_value=0, allow_nan=False, allow_infinity=False),
    discount_percentage=st.floats(
        min_value=0, max_value=100, allow_nan=False, allow_infinity=False
    ),
)
def test_a_discounted_price_is_not_higher_than_the_original_price(
    price, discount_percentage
):
    product = Product(price)
    assert product.get_discount_price(discount_percentage) <= product.price
