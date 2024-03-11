# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

REVEALED_TYPES = [
    ("integers()", "int"),
    ("text()", "str"),
    ("integers().map(str)", "str"),
    ("booleans().filter(bool)", "bool"),
    ("tuples()", "Tuple[()]"),
    ("tuples(integers())", "Tuple[int]"),
    ("tuples(integers(), text())", "Tuple[int, str]"),
    (
        "tuples(integers(), text(), integers(), text(), integers())",
        "Tuple[int, str, int, str, int]",
    ),
    (
        "tuples(text(), text(), text(), text(), text(), text())",
        "Tuple[Any, ...]",
    ),
]

NUMPY_REVEALED_TYPES = [
    (
        'arrays(dtype=np.dtype("int32"), shape=1)',
        "ndarray[Any, dtype[signedinteger[_32Bit]]]",
    ),
    (
        "arrays(dtype=np.dtype(int), shape=1)",
        "ndarray[Any, dtype[signedinteger[Any]]]",
    ),
    (
        "boolean_dtypes()",
        "dtype[bool_]",
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
        "dtype[floating[_64Bit]]",
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
        "dtype[complexfloating[_64Bit, _64Bit]]",
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
        "Tuple[ndarray[Any, dtype[signedinteger[Any]]], ...]",
    ),
    (
        'integer_array_indices(shape=(2, 3), dtype=np.dtype("int32"))',
        "Tuple[ndarray[Any, dtype[signedinteger[_32Bit]]], ...]",
    ),
    (
        'integer_array_indices(shape=(2, 3), dtype=np.dtype("uint8"))',
        "Tuple[ndarray[Any, dtype[unsignedinteger[_8Bit]]], ...]",
    ),
]
