# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import sys

import numpy as np
import pytest

from hypothesis import assume, given, settings, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.extra import numpy as nps
from hypothesis.internal.floats import width_smallest_normals
from hypothesis.strategies._internal import SearchStrategy

from tests.common.debug import assert_no_examples, check_can_generate_examples, find_any

np_version = tuple(int(x) for x in np.__version__.split(".")[:2])

STANDARD_TYPES = [
    np.dtype(t)
    for t in (
        "int8",
        "int16",
        "int32",
        "int64",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "float",
        "float16",
        "float32",
        "float64",
        "complex64",
        "complex128",
        "datetime64",
        "timedelta64",
        bool,
        str,
        bytes,
    )
]
for nonstandard_typecode in ["g", "G", "S1", "q", "Q"]:
    try:
        STANDARD_TYPES.append(np.dtype(nonstandard_typecode))
    except Exception:
        pass


@given(nps.nested_dtypes())
def test_strategies_for_standard_dtypes_have_reusable_values(dtype):
    assert nps.from_dtype(dtype).has_reusable_values


@pytest.mark.parametrize("t", STANDARD_TYPES)
def test_produces_instances(t):
    @given(nps.from_dtype(t))
    def test_is_t(x):
        assert isinstance(x, t.type)
        assert x.dtype.kind == t.kind

    test_is_t()


@settings(max_examples=100, deadline=None)
@given(nps.nested_dtypes(max_itemsize=400), st.data())
def test_infer_strategy_from_dtype(dtype, data):
    # Given a dtype
    assert isinstance(dtype, np.dtype)
    # We can infer a strategy
    strat = nps.from_dtype(dtype)
    assert isinstance(strat, SearchStrategy)
    # And use it to fill an array of that dtype
    data.draw(nps.arrays(dtype, 10, elements=strat))


@given(st.data())
def test_can_cast_for_scalars(data):
    # Note: this only passes with castable datatypes, certain dtype
    # combinations will result in an error if numpy is not able to cast them.
    dt_elements = np.dtype(data.draw(st.sampled_from(["bool", "<i2", ">i2"])))
    dt_desired = np.dtype(
        data.draw(st.sampled_from(["<i2", ">i2", "float32", "float64"]))
    )
    result = data.draw(
        nps.arrays(dtype=dt_desired, elements=nps.from_dtype(dt_elements), shape=())
    )
    assert isinstance(result, np.ndarray)
    assert result.dtype == dt_desired


@given(st.data())
def test_unicode_string_dtypes_generate_unicode_strings(data):
    dt = data.draw(nps.unicode_string_dtypes())
    result = data.draw(nps.from_dtype(dt))
    assert isinstance(result, str)


@given(nps.arrays(dtype="U99", shape=(10,)))
def test_can_unicode_strings_without_decode_error(arr):
    # See https://github.com/numpy/numpy/issues/15363
    pass


@pytest.mark.skipif(not nps.NP_FIXED_UNICODE, reason="workaround for old bug")
def test_unicode_string_dtypes_need_not_be_utf8():
    def cannot_encode(string):
        try:
            string.encode()
            return False
        except UnicodeEncodeError:
            return True

    find_any(nps.from_dtype(np.dtype("U")), cannot_encode, settings(max_examples=5000))


@given(st.data())
def test_byte_string_dtypes_generate_unicode_strings(data):
    dt = data.draw(nps.byte_string_dtypes())
    result = data.draw(nps.from_dtype(dt))
    assert isinstance(result, bytes)


skipif_np2 = pytest.mark.skipif(np_version >= (2, 0), reason="removed in new version")


@pytest.mark.parametrize(
    "dtype",
    ["U", "S", pytest.param("a", marks=skipif_np2)],
)
def test_unsized_strings_length_gt_one(dtype):
    # See https://github.com/HypothesisWorks/hypothesis/issues/2229
    find_any(nps.arrays(dtype=dtype, shape=1), lambda arr: len(arr[0]) >= 2)


@given(
    st.data(),
    st.builds(
        "{}[{}]".format,
        st.sampled_from(("datetime64", "timedelta64")),
        st.sampled_from(nps.TIME_RESOLUTIONS),
    ).map(np.dtype),
)
def test_inferring_from_time_dtypes_gives_same_dtype(data, dtype):
    ex = data.draw(nps.from_dtype(dtype))
    assert dtype == ex.dtype


@given(st.data(), nps.byte_string_dtypes() | nps.unicode_string_dtypes())
def test_inferred_string_strategies_roundtrip(data, dtype):
    # Check that we never generate too-long or nul-terminated strings, which
    # cannot be read back out of an array.
    arr = np.zeros(shape=1, dtype=dtype)
    ex = data.draw(nps.from_dtype(arr.dtype))
    arr[0] = ex
    assert arr[0] == ex


@given(st.data(), nps.scalar_dtypes())
def test_all_inferred_scalar_strategies_roundtrip(data, dtype):
    # We only check scalars here, because record/compound/nested dtypes always
    # give an array of np.void objects.  We're interested in whether scalar
    # values are safe, not known type coercion.
    arr = np.zeros(shape=1, dtype=dtype)
    ex = data.draw(nps.from_dtype(arr.dtype))
    assume(ex == ex)  # If not, the roundtrip test *should* fail!  (eg NaN)
    arr[0] = ex
    assert arr[0] == ex


@pytest.mark.parametrize("dtype_str", ["m8", "M8"])
@given(data=st.data())
def test_from_dtype_works_without_time_unit(data, dtype_str):
    arr = data.draw(nps.from_dtype(np.dtype(dtype_str)))
    assert (dtype_str + "[") in arr.dtype.str


@pytest.mark.parametrize("dtype_str", ["m8", "M8"])
@given(data=st.data())
def test_arrays_selects_consistent_time_unit(data, dtype_str):
    arr = data.draw(nps.arrays(dtype_str, 10))
    assert (dtype_str + "[") in arr.dtype.str


@pytest.mark.parametrize("dtype", ["m8", "M8"])
def test_from_dtype_can_include_or_exclude_nat(dtype):
    find_any(nps.from_dtype(np.dtype(dtype), allow_nan=None), np.isnat)
    find_any(nps.from_dtype(np.dtype(dtype), allow_nan=True), np.isnat)
    assert_no_examples(nps.from_dtype(np.dtype(dtype), allow_nan=False), np.isnat)


def test_arrays_gives_useful_error_on_inconsistent_time_unit():
    with pytest.raises(InvalidArgument, match="mismatch of time units in dtypes"):
        check_can_generate_examples(
            nps.arrays("m8[Y]", 10, elements=nps.from_dtype(np.dtype("m8[D]")))
        )


@pytest.mark.parametrize(
    "dtype, kwargs, pred",
    [
        # Floating point: bounds, exclusive bounds, and excluding nonfinites
        (float, {"min_value": 1, "max_value": 2}, lambda x: 1 <= x <= 2),
        (
            float,
            {"min_value": 1, "max_value": 2, "exclude_min": True, "exclude_max": True},
            lambda x: 1 < x < 2,
        ),
        (float, {"allow_nan": False}, lambda x: not np.isnan(x)),
        (float, {"allow_infinity": False}, lambda x: not np.isinf(x)),
        (float, {"allow_nan": False, "allow_infinity": False}, np.isfinite),
        # Complex numbers: bounds and excluding nonfinites
        (complex, {"allow_nan": False}, lambda x: not np.isnan(x)),
        (complex, {"allow_infinity": False}, lambda x: not np.isinf(x)),
        (complex, {"allow_nan": False, "allow_infinity": False}, np.isfinite),
        # Note we accept epsilon errors here as internally sqrt is used to draw
        # complex numbers. sqrt on some platforms gets epsilon errors, which is
        # too tricky to filter out and so - for now - we just accept them.
        (
            complex,
            {"min_magnitude": 1e3},
            lambda x: abs(x) >= 1e3 * (1 - sys.float_info.epsilon),
        ),
        (
            complex,
            {"max_magnitude": 1e2},
            lambda x: abs(x) <= 1e2 * (1 + sys.float_info.epsilon),
        ),
        (
            complex,
            {"min_magnitude": 1, "max_magnitude": 1e6},
            lambda x: (
                (1 - sys.float_info.epsilon)
                <= abs(x)
                <= 1e6 * (1 + sys.float_info.epsilon)
            ),
        ),
        # Integer bounds, limited to the representable range
        ("int8", {"min_value": -1, "max_value": 1}, lambda x: -1 <= x <= 1),
        ("uint8", {"min_value": 1, "max_value": 2}, lambda x: 1 <= x <= 2),
        # String arguments, bounding size and unicode alphabet
        ("S", {"min_size": 1, "max_size": 2}, lambda x: 1 <= len(x) <= 2),
        ("S4", {"min_size": 1, "max_size": 2}, lambda x: 1 <= len(x) <= 2),
        ("U", {"min_size": 1, "max_size": 2}, lambda x: 1 <= len(x) <= 2),
        ("U4", {"min_size": 1, "max_size": 2}, lambda x: 1 <= len(x) <= 2),
        ("U", {"alphabet": "abc"}, lambda x: set(x).issubset("abc")),
    ],
)
@given(data=st.data())
def test_from_dtype_with_kwargs(data, dtype, kwargs, pred):
    value = data.draw(nps.from_dtype(np.dtype(dtype), **kwargs))
    assert pred(value)


@given(nps.from_dtype(np.dtype("U20,uint8,float32"), min_size=1, allow_nan=False))
def test_customize_structured_dtypes(x):
    name, age, score = x
    assert len(name) >= 1
    assert 0 <= age <= 255
    assert not np.isnan(score)


@pytest.mark.parametrize("allow_subnormal", [False, True])
@pytest.mark.parametrize("width", [32, 64])
def test_float_subnormal_generation(allow_subnormal, width):
    dtype = np.dtype(f"float{width}")
    strat = nps.from_dtype(dtype, allow_subnormal=allow_subnormal).filter(
        lambda n: n != 0
    )
    smallest_normal = width_smallest_normals[width]
    if allow_subnormal:
        find_any(strat, lambda n: -smallest_normal < n < smallest_normal)
    else:
        assert_no_examples(strat, lambda n: -smallest_normal < n < smallest_normal)


@pytest.mark.parametrize("allow_subnormal", [False, True])
@pytest.mark.parametrize("width", [64, 128])
def test_complex_subnormal_generation(allow_subnormal, width):
    dtype = np.dtype(f"complex{width}")
    strat = nps.from_dtype(dtype, allow_subnormal=allow_subnormal).filter(
        lambda n: n.real != 0 and n.imag != 0
    )
    smallest_normal = width_smallest_normals[width / 2]

    def condition(n):
        return (
            -smallest_normal < n.real < smallest_normal
            or -smallest_normal < n.imag < smallest_normal
        )

    if allow_subnormal:
        find_any(strat, condition)
    else:
        assert_no_examples(strat, condition)
