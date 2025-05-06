# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import re

from hypothesistooling.__main__ import PYTHONS as pythons_map

PYTHON_VERSIONS = [v for v in pythons_map if re.fullmatch(r"3\.\d\d?", v)]

try:
    from numpy import __version__ as np_version
except ImportError:
    NP1 = False
else:
    NP1 = np_version.startswith("1.")

REVEALED_TYPES = [
    ("integers()", "int"),
    ("text()", "str"),
    ("integers().map(str)", "str"),
    ("booleans().filter(bool)", "bool"),
    ("tuples()", "tuple[()]"),
    ("tuples(integers())", "tuple[int]"),
    ("tuples(integers(), text())", "tuple[int, str]"),
    (
        "tuples(integers(), text(), integers(), text(), integers())",
        "tuple[int, str, int, str, int]",
    ),
    (
        "tuples(text(), text(), text(), text(), text(), text())",
        "tuple[Any, ...]",
    ),
    ("lists(none())", "list[None]"),
    ("integers().filter(lambda x: x > 0)", "int"),
    ("booleans().filter(lambda x: x)", "bool"),
    ("integers().map(bool).filter(lambda x: x)", "bool"),
    ("integers().flatmap(lambda x: lists(floats()))", "list[float]"),
    ("one_of([integers(), integers()])", "int"),
    ("one_of([integers(), floats()])", "float"),
]

NUMPY_REVEALED_TYPES = [
    (
        'arrays(dtype=np.dtype("int32"), shape=1)',
        "ndarray[tuple[int, ...], dtype[signedinteger[_32Bit]]]",
    ),
    (
        "arrays(dtype=np.dtype(int), shape=1)",
        "ndarray[tuple[int, ...], dtype[Union[signedinteger[Union[_32Bit, _64Bit]], bool[bool]]]]",
    ),
    (
        "boolean_dtypes()",
        "dtype[bool[bool]]",  # np.bool[builtins.bool]
    ),
    (
        "unsigned_integer_dtypes(sizes=8)",
        "dtype[unsignedinteger[_8Bit]]",
    ),
    (
        "unsigned_integer_dtypes(sizes=16)",
        "dtype[unsignedinteger[_16Bit]]",
    ),
    (
        "unsigned_integer_dtypes(sizes=32)",
        "dtype[unsignedinteger[_32Bit]]",
    ),
    (
        "unsigned_integer_dtypes(sizes=64)",
        "dtype[unsignedinteger[_64Bit]]",
    ),
    (
        "unsigned_integer_dtypes()",
        "dtype[unsignedinteger[Any]]",
    ),
    (
        "unsigned_integer_dtypes(sizes=(8, 16))",
        "dtype[unsignedinteger[Any]]",
    ),
    (
        "integer_dtypes(sizes=8)",
        "dtype[signedinteger[_8Bit]]",
    ),
    (
        "integer_dtypes(sizes=16)",
        "dtype[signedinteger[_16Bit]]",
    ),
    (
        "integer_dtypes(sizes=32)",
        "dtype[signedinteger[_32Bit]]",
    ),
    (
        "integer_dtypes(sizes=64)",
        "dtype[signedinteger[_64Bit]]",
    ),
    (
        "integer_dtypes()",
        "dtype[signedinteger[Any]]",
    ),
    (
        "integer_dtypes(sizes=(8, 16))",
        "dtype[signedinteger[Any]]",
    ),
    (
        "floating_dtypes(sizes=16)",
        "dtype[floating[_16Bit]]",
    ),
    (
        "floating_dtypes(sizes=32)",
        "dtype[floating[_32Bit]]",
    ),
    (
        "floating_dtypes(sizes=64)",
        "dtype[float64]",
    ),
    (
        "floating_dtypes(sizes=128)",
        "dtype[floating[_128Bit]]",
    ),
    (
        "floating_dtypes()",
        "dtype[floating[Any]]",
    ),
    (
        "floating_dtypes(sizes=(16, 32))",
        "dtype[floating[Any]]",
    ),
    (
        "complex_number_dtypes(sizes=64)",
        "dtype[complexfloating[_32Bit, _32Bit]]",
    ),
    (
        "complex_number_dtypes(sizes=128)",
        "dtype[complex128]",
    ),
    (
        "complex_number_dtypes(sizes=256)",
        "dtype[complexfloating[_128Bit, _128Bit]]",
    ),
    (
        "complex_number_dtypes()",
        "dtype[complexfloating[Any, Any]]",
    ),
    (
        "complex_number_dtypes(sizes=(64, 128))",
        "dtype[complexfloating[Any, Any]]",
    ),
    (
        "integer_array_indices(shape=(2, 3))",
        "tuple[ndarray[tuple[int, ...], dtype[signedinteger[Any]]], ...]",
    ),
    (
        'integer_array_indices(shape=(2, 3), dtype=np.dtype("int32"))',
        "tuple[ndarray[tuple[int, ...], dtype[signedinteger[_32Bit]]], ...]",
    ),
    (
        'integer_array_indices(shape=(2, 3), dtype=np.dtype("uint8"))',
        "tuple[ndarray[tuple[int, ...], dtype[unsignedinteger[_8Bit]]], ...]",
    ),
]
