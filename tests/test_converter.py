from tests.common.descriptors import DescriptorWithValue
from tests.common import small_table
from hypothesis import given, assume, Verifier
from hypothesis.database.converter import (
    NotSerializeable, ConverterTable, WrongFormat
)
import hypothesis.settings as hs
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.searchstrategy import RandomWithSeed
from hypothesis.descriptors import Just, OneOf, SampledFrom
import pytest
from random import Random


@pytest.mark.parametrize(('descriptor', 'value'), [
    ({int}, 0),
    (text_type, 0),
    (binary_type, RandomWithSeed(1)),
    (Just([]), 1),
    (Random, False),
    (complex, {1}),
    ((int, int), ('', '')),
    ((int, int), 'hi'),
    ((text_type, text_type), 'hi'),
    ((int, float, str, bytes, bool, complex), 0),
    (OneOf((int, float)), {0}),
    ({220: int, 437: int}, ''),
    ([binary_type], 0),
    (SampledFrom([1, 2, 3]), 0),

])
def test_simple_conversions(descriptor, value):
    converter = ConverterTable.default().specification_for(descriptor)
    with pytest.raises(WrongFormat):
        converter.to_json(value)


@given(DescriptorWithValue, DescriptorWithValue, verifier=Verifier(
    strategy_table=small_table,
    settings=hs.Settings(max_examples=500),
))
def test_can_not_save_as_incompatible_examples(dav, dav2):
    strategy = small_table.strategy(dav.descriptor)
    assume(not strategy.could_have_produced(dav2.value))
    ft = ConverterTable.default()
    try:
        converter = ft.specification_for(dav.descriptor)
    except NotSerializeable:
        assume(False)

    with pytest.raises(WrongFormat):
        converter.to_json(dav2.value)
