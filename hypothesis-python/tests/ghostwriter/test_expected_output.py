# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

"""
'Golden master' tests for the ghostwriter.

To update the recorded outputs, run `pytest --hypothesis-update-outputs ...`.
"""

import ast
import base64
import operator
import pathlib
import re
from typing import Sequence

import numpy
import pytest

from hypothesis.extra import ghostwriter


@pytest.fixture
def update_recorded_outputs(request):
    return request.config.getoption("--hypothesis-update-outputs")


def timsort(seq: Sequence[int]) -> Sequence[int]:
    return sorted(seq)


class A_Class:
    @classmethod
    def a_classmethod(cls, arg: int):
        pass


def add(a: float, b: float) -> float:
    return a + b


# Note: for some of the `expected` outputs, we replace away some small
#       parts which vary between minor versions of Python.
@pytest.mark.parametrize(
    "data",
    [
        ("fuzz_sorted", ghostwriter.fuzz(sorted)),
        ("fuzz_classmethod", ghostwriter.fuzz(A_Class.a_classmethod)),
        ("fuzz_ufunc", ghostwriter.fuzz(numpy.add)),
        ("magic_gufunc", ghostwriter.magic(numpy.matmul)),
        ("re_compile", ghostwriter.fuzz(re.compile)),
        (
            "re_compile_except",
            ghostwriter.fuzz(re.compile, except_=re.error)
            # re.error fixed it's __module__ in Python 3.7
            .replace("import sre_constants\n", "").replace("sre_constants.", "re."),
        ),
        ("re_compile_unittest", ghostwriter.fuzz(re.compile, style="unittest")),
        ("base64_magic", ghostwriter.magic(base64)),
        ("sorted_idempotent", ghostwriter.idempotent(sorted)),
        ("timsort_idempotent", ghostwriter.idempotent(timsort)),
        ("eval_equivalent", ghostwriter.equivalent(eval, ast.literal_eval)),
        ("sorted_self_equivalent", ghostwriter.equivalent(sorted, sorted, sorted)),
        ("addition_op_magic", ghostwriter.magic(add)),
        ("addition_op_multimagic", ghostwriter.magic(add, operator.add, numpy.add)),
        (
            "division_operator",
            ghostwriter.binary_operation(
                operator.truediv, associative=False, commutative=False
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
    ],
    ids=lambda x: x[0],
)
def test_ghostwriter_example_outputs(update_recorded_outputs, data):
    name, actual = data
    file_ = pathlib.Path(__file__).parent / "recorded" / f"{name}.txt"
    if update_recorded_outputs:
        file_.write_text(actual)
    expected = file_.read_text()
    assert actual == expected  # We got the expected source code
    exec(expected, {})  # and there are no SyntaxError or NameErrors
