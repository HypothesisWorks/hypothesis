# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""
'Golden master' tests for the ghostwriter.

To update the recorded outputs, run `pytest --hypothesis-update-outputs ...`.
"""

import ast
import base64
import builtins
import collections.abc
import operator
import pathlib
import re
import sys
from typing import Optional, Sequence, Union

import numpy
import numpy.typing
import pytest
from example_code.future_annotations import (
    add_custom_classes,
    invalid_types,
    merge_dicts,
)

import hypothesis
from hypothesis.extra import ghostwriter
from hypothesis.utils.conventions import not_set


@pytest.fixture
def update_recorded_outputs(request):
    return request.config.getoption("--hypothesis-update-outputs")


def get_recorded(name, actual=""):
    file_ = pathlib.Path(__file__).parent / "recorded" / f"{name}.txt"
    if actual:
        file_.write_text(actual, encoding="utf-8")
    return file_.read_text(encoding="utf-8")


def timsort(seq: Sequence[int]) -> Sequence[int]:
    return sorted(seq)


def with_docstring(a, b, c, d=int, e=lambda x: f"xx{x}xx") -> None:
    """Demonstrates parsing params from the docstring

    :param a: sphinx docstring style
    :type a: sequence of integers

    b (list, tuple, or None): Google docstring style

    c : {"foo", "bar", or None}
        Numpy docstring style
    """


class A_Class:
    @classmethod
    def a_classmethod(cls, arg: int):
        pass

    @staticmethod
    def a_staticmethod(arg: int):
        pass


def add(a: float, b: float) -> float:
    return a + b


def divide(a: int, b: int) -> float:
    """This is a RST-style docstring for `divide`.

    :raises ZeroDivisionError: if b == 0
    """
    return a / b


def optional_parameter(a: float, b: Optional[float]) -> float:
    return optional_union_parameter(a, b)


def optional_union_parameter(a: float, b: Optional[Union[float, int]]) -> float:
    return a if b is None else a + b


if sys.version_info[:2] >= (3, 10):

    def union_sequence_parameter(items: Sequence[float | int]) -> float:
        return sum(items)

else:

    def union_sequence_parameter(items: Sequence[Union[float, int]]) -> float:
        return sum(items)


if sys.version_info[:2] >= (3, 9):
    CollectionsSequence = collections.abc.Sequence
else:
    # in older versions collections.abc was not generic
    CollectionsSequence = Sequence


def sequence_from_collections(items: CollectionsSequence[int]) -> int:
    return min(items)


def various_numpy_annotations(
    f: numpy.typing.NDArray[numpy.float64],
    fc: numpy.typing.NDArray[numpy.float64 | numpy.complex128],
    union: numpy.typing.NDArray[numpy.float64 | numpy.complex128] | None,
):
    pass


# Note: for some of the `expected` outputs, we replace away some small
#       parts which vary between minor versions of Python.
@pytest.mark.parametrize(
    "data",
    [
        ("fuzz_sorted", ghostwriter.fuzz(sorted)),
        ("fuzz_sorted_with_annotations", ghostwriter.fuzz(sorted, annotate=True)),
        ("fuzz_with_docstring", ghostwriter.fuzz(with_docstring)),
        ("fuzz_classmethod", ghostwriter.fuzz(A_Class.a_classmethod)),
        ("fuzz_staticmethod", ghostwriter.fuzz(A_Class.a_staticmethod)),
        ("fuzz_ufunc", ghostwriter.fuzz(numpy.add)),
        ("magic_gufunc", ghostwriter.magic(numpy.matmul)),
        pytest.param(
            ("optional_parameter", ghostwriter.magic(optional_parameter)),
            marks=pytest.mark.skipif("sys.version_info[:2] < (3, 9)"),
        ),
        pytest.param(
            ("optional_parameter_pre_py_3_9", ghostwriter.magic(optional_parameter)),
            marks=pytest.mark.skipif("sys.version_info[:2] >= (3, 9)"),
        ),
        ("optional_union_parameter", ghostwriter.magic(optional_union_parameter)),
        ("union_sequence_parameter", ghostwriter.magic(union_sequence_parameter)),
        pytest.param(
            ("sequence_from_collections", ghostwriter.magic(sequence_from_collections)),
            marks=pytest.mark.skipif("sys.version_info[:2] < (3, 9)"),
        ),
        pytest.param(
            ("add_custom_classes", ghostwriter.magic(add_custom_classes)),
            marks=pytest.mark.skipif("sys.version_info[:2] < (3, 10)"),
        ),
        pytest.param(
            ("merge_dicts", ghostwriter.magic(merge_dicts)),
            marks=pytest.mark.skipif("sys.version_info[:2] < (3, 10)"),
        ),
        pytest.param(
            ("invalid_types", ghostwriter.magic(invalid_types)),
            marks=pytest.mark.skipif("sys.version_info[:2] < (3, 10)"),
        ),
        ("magic_base64_roundtrip", ghostwriter.magic(base64.b64encode)),
        (
            "magic_base64_roundtrip_with_annotations",
            ghostwriter.magic(base64.b64encode, annotate=True),
        ),
        ("re_compile", ghostwriter.fuzz(re.compile)),
        (
            "re_compile_except",
            ghostwriter.fuzz(re.compile, except_=re.error)
            # re.error fixed it's __module__ in Python 3.7
            .replace("import sre_constants\n", "").replace("sre_constants.", "re."),
        ),
        ("re_compile_unittest", ghostwriter.fuzz(re.compile, style="unittest")),
        pytest.param(
            ("base64_magic", ghostwriter.magic(base64)),
            marks=pytest.mark.skipif("sys.version_info[:2] >= (3, 10)"),
        ),
        ("sorted_idempotent", ghostwriter.idempotent(sorted)),
        ("timsort_idempotent", ghostwriter.idempotent(timsort)),
        (
            "timsort_idempotent_asserts",
            ghostwriter.idempotent(timsort, except_=AssertionError),
        ),
        ("eval_equivalent", ghostwriter.equivalent(eval, ast.literal_eval)),
        ("sorted_self_equivalent", ghostwriter.equivalent(sorted, sorted, sorted)),
        (
            "sorted_self_equivalent_with_annotations",
            ghostwriter.equivalent(sorted, sorted, sorted, annotate=True),
        ),
        ("addition_op_magic", ghostwriter.magic(add)),
        ("multiplication_magic", ghostwriter.magic(operator.mul)),
        ("matmul_magic", ghostwriter.magic(operator.matmul)),
        ("addition_op_multimagic", ghostwriter.magic(add, operator.add, numpy.add)),
        ("division_fuzz_error_handler", ghostwriter.fuzz(divide)),
        (
            "division_binop_error_handler",
            ghostwriter.binary_operation(divide, identity=1),
        ),
        (
            "division_roundtrip_error_handler",
            ghostwriter.roundtrip(divide, operator.mul),
        ),
        (
            "division_roundtrip_error_handler_without_annotations",
            ghostwriter.roundtrip(divide, operator.mul, annotate=False),
        ),
        (
            "division_roundtrip_arithmeticerror_handler",
            ghostwriter.roundtrip(divide, operator.mul, except_=ArithmeticError),
        ),
        (
            "division_roundtrip_typeerror_handler",
            ghostwriter.roundtrip(divide, operator.mul, except_=TypeError),
        ),
        (
            "division_operator",
            ghostwriter.binary_operation(
                operator.truediv, associative=False, commutative=False
            ),
        ),
        (
            "division_operator_with_annotations",
            ghostwriter.binary_operation(
                operator.truediv, associative=False, commutative=False, annotate=True
            ),
        ),
        (
            "multiplication_operator",
            ghostwriter.binary_operation(
                operator.mul, identity=1, distributes_over=operator.add
            ),
        ),
        (
            "multiplication_operator_unittest",
            ghostwriter.binary_operation(
                operator.mul,
                identity=1,
                distributes_over=operator.add,
                style="unittest",
            ),
        ),
        (
            "sorted_self_error_equivalent_simple",
            ghostwriter.equivalent(sorted, sorted, allow_same_errors=True),
        ),
        (
            "sorted_self_error_equivalent_threefuncs",
            ghostwriter.equivalent(sorted, sorted, sorted, allow_same_errors=True),
        ),
        (
            "sorted_self_error_equivalent_1error",
            ghostwriter.equivalent(
                sorted,
                sorted,
                allow_same_errors=True,
                except_=ValueError,
            ),
        ),
        (
            "sorted_self_error_equivalent_2error_unittest",
            ghostwriter.equivalent(
                sorted,
                sorted,
                allow_same_errors=True,
                except_=(TypeError, ValueError),
                style="unittest",
            ),
        ),
        ("magic_class", ghostwriter.magic(A_Class)),
        pytest.param(
            ("magic_builtins", ghostwriter.magic(builtins)),
            marks=[
                pytest.mark.skipif(
                    sys.version_info[:2] != (3, 10),
                    reason="often small changes",
                )
            ],
        ),
        ("magic_numpy", ghostwriter.magic(various_numpy_annotations, annotate=False)),
    ],
    ids=lambda x: x[0],
)
def test_ghostwriter_example_outputs(update_recorded_outputs, data):
    name, actual = data
    expected = get_recorded(name, actual * update_recorded_outputs)
    assert actual == expected  # We got the expected source code
    exec(expected, {})  # and there are no SyntaxError or NameErrors


def test_ghostwriter_on_hypothesis(update_recorded_outputs):
    actual = ghostwriter.magic(hypothesis).replace("Strategy[+Ex]", "Strategy")
    expected = get_recorded("hypothesis_module_magic", actual * update_recorded_outputs)
    if sys.version_info[:2] == (3, 10):
        assert actual == expected
    exec(expected, {"not_set": not_set})
