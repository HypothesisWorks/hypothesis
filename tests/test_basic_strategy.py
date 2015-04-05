import gc
import pytest

from hypothesis.searchstrategy import basic_strategy
from hypothesis.internal.compat import hrange
from hypothesis.strategytests import strategy_test_suite
from hypothesis import given


def simplify_bitfield(random, value):
    for i in hrange(128):
        k = 1 << i
        if value & k:
            yield value & (~k)

BitField = basic_strategy(
    generate=lambda r, p: r.getrandbits(128),
    simplify=simplify_bitfield,
    copy=lambda x: x,
)


TestBitfield = strategy_test_suite(BitField)


def test_cache_is_cleaned_up_on_gc_1():
    st = basic_strategy(
        generate=lambda r, p: r.getrandbits(128),
        simplify=simplify_bitfield,
        copy=lambda x: x,
    )

    @given(st)
    def test_all_good(x):
        pass

    test_all_good()

    gc.collect()

    assert len(st.reify_cache) == 0


def test_cache_is_cleaned_up_on_gc_2():
    st = basic_strategy(
        generate=lambda r, p: r.getrandbits(128),
        simplify=simplify_bitfield,
        copy=lambda x: x,
    )

    @given(st)
    def test_all_bad(x):
        assert False

    gc.collect()

    with pytest.raises(AssertionError):
        test_all_bad()

    assert len(st.reify_cache) == 0
