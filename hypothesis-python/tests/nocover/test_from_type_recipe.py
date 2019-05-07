from __future__ import absolute_import, division, print_function

import datetime
import decimal
import fractions
import numbers
import uuid

import hypothesis.strategies as st
from hypothesis import given, settings


def everything_except(excluded_types):
    return (
        st.from_type(type)
        .flatmap(lambda x: st.from_type(x))
        .filter(lambda x: not isinstance(x, excluded_types))
    )


many_types = [
    bool,
    bytearray,
    bytes,
    complex,
    datetime.date,
    datetime.datetime,
    datetime.time,
    datetime.timedelta,
    decimal.Decimal,
    dict,
    float,
    fractions.Fraction,
    frozenset,
    int,
    list,
    memoryview,
    numbers.Complex,
    numbers.Integral,
    numbers.Number,
    numbers.Rational,
    numbers.Real,
    range,
    set,
    slice,
    str,
    tuple,
    uuid.UUID,
]


# TODO failing seed: @seed(3239923953324650810165101787612320707)


@settings(max_examples=5000)
@given(
    excluded_types=st.lists(
        st.sampled_from(many_types), min_size=1, max_size=3, unique=True
    ).map(tuple),
    data=st.data(),
)
def test_everything_but_recipe(excluded_types, data):
    value = data.draw(everything_except(excluded_types), label="value")
    assert not isinstance(value, excluded_types)
