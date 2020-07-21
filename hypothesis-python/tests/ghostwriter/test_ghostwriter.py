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

import ast
import enum
import json
import re
import unittest
from decimal import Decimal
from types import ModuleType
from typing import List, Sequence, Set

import pytest

from hypothesis.errors import InvalidArgument, MultipleFailures, Unsatisfiable
from hypothesis.extra import ghostwriter
from hypothesis.strategies import just

varied_excepts = pytest.mark.parametrize("ex", [(), ValueError, (TypeError, re.error)])


def get_test_function(source_code):
    # A helper function to get the dynamically-defined test function.
    # Note that this also tests that the module is syntatically-valid,
    # AND free from undefined names, import problems, and so on.
    namespace = {}
    try:
        exec(source_code, namespace)
    except SyntaxError:
        print(source_code)
        raise
    tests = [
        v
        for k, v in namespace.items()
        if k.startswith(("test_", "Test")) and not isinstance(v, ModuleType)
    ]
    assert len(tests) == 1, tests
    return tests[0]


@pytest.mark.parametrize(
    "badness", ["not an exception", BaseException, [ValueError], (Exception, "bad")]
)
def test_invalid_exceptions(badness):
    with pytest.raises(InvalidArgument):
        ghostwriter._check_except(badness)


class AnEnum(enum.Enum):
    a = "value of AnEnum.a"
    b = "value of AnEnum.b"


def takes_enum(foo=AnEnum.a):
    # This can only fail if we use the default argument to guess
    # that any instance of that enum type should be allowed.
    assert foo != AnEnum.b


def test_ghostwriter_exploits_arguments_with_enum_defaults():
    source_code = ghostwriter.fuzz(takes_enum)
    test = get_test_function(source_code)
    with pytest.raises(AssertionError):
        test()


def timsort(seq: Sequence[int]) -> List[int]:
    return sorted(seq)


@varied_excepts
@pytest.mark.parametrize(
    "func", [re.compile, json.loads, json.dump, timsort, ast.literal_eval]
)
def test_ghostwriter_fuzz(func, ex):
    source_code = ghostwriter.fuzz(func, except_=ex)
    get_test_function(source_code)


@varied_excepts
@pytest.mark.parametrize(
    "func", [re.compile, json.loads, json.dump, timsort, ast.literal_eval]
)
def test_ghostwriter_unittest_style(func, ex):
    source_code = ghostwriter.fuzz(func, except_=ex, style="unittest")
    assert issubclass(get_test_function(source_code), unittest.TestCase)


def no_annotations(foo=None, bar=False):
    pass


def test_inference_from_defaults_and_none_booleans_reprs_not_just_and_sampled_from():
    source_code = ghostwriter.fuzz(no_annotations)
    assert "@given(foo=st.none(), bar=st.booleans())" in source_code


@varied_excepts
@pytest.mark.parametrize("func", [sorted, timsort])
def test_ghostwriter_idempotent(func, ex):
    source_code = ghostwriter.idempotent(func, except_=ex)
    test = get_test_function(source_code)
    if "=st.nothing()" in source_code:
        with pytest.raises(Unsatisfiable):
            test()
    else:
        test()


def hopefully_hashable(foo: Set[Decimal]):
    pass


def test_no_hashability_filter():
    # In from_type, we ordinarily protect users from really weird cases like
    # `Decimal('snan')` - a unhashable value of a hashable type - but in the
    # ghostwriter we instead want to present this to the user for an explicit
    # decision.  They can pass `allow_nan=False`, fix their custom type's
    # hashing logic, or whatever else; simply doing nothing will usually work.
    source_code = ghostwriter.fuzz(hopefully_hashable)
    assert "_can_hash" not in source_code
    test = get_test_function(source_code)
    with pytest.raises(TypeError, match="[Cc]annot hash a signaling NaN"):
        test()


@pytest.mark.parametrize(
    "gw,args",
    [
        (ghostwriter.fuzz, ["not callable"]),
        (ghostwriter.idempotent, ["not callable"]),
        (ghostwriter.roundtrip, []),
        (ghostwriter.roundtrip, ["not callable"]),
        (ghostwriter.equivalent, [sorted]),
        (ghostwriter.equivalent, [sorted, "not callable"]),
    ],
)
def test_invalid_func_inputs(gw, args):
    with pytest.raises(InvalidArgument):
        gw(*args)


def test_run_ghostwriter_idempotent():
    # This test covers the whole lifecycle: first, we get the default code.
    # The first argument is unknown, so we fail to draw from st.nothing()
    source_code = ghostwriter.idempotent(sorted)
    with pytest.raises(Unsatisfiable):
        get_test_function(source_code)()
    # Replacing that nothing() with a strategy for sequences of integers makes the
    # test pass, incidentally checking our handling of positional-only arguments.
    source_code = source_code.replace("st.nothing()", "st.lists(st.integers())")
    get_test_function(source_code)()


def test_run_ghostwriter_roundtrip():
    # This test covers the whole lifecycle: first, we get the default code.
    # The first argument is unknown, so we fail to draw from st.nothing()
    source_code = ghostwriter.roundtrip(json.dumps, json.loads)
    with pytest.raises(Unsatisfiable):
        get_test_function(source_code)()

    # Replacing that nothing() with a strategy for JSON allows us to discover
    # two possible failures: `nan` is not equal to itself, and if dumps is
    # passed allow_nan=False it is a ValueError to pass a non-finite float.
    source_code = source_code.replace(
        "st.nothing()",
        "st.recursive(st.one_of(st.none(), st.booleans(), st.floats(), st.text()), "
        "lambda v: st.lists(v, max_size=2) | st.dictionaries(st.text(), v, max_size=2)"
        ", max_leaves=2)",
    )
    try:
        get_test_function(source_code)()
    except (AssertionError, ValueError, MultipleFailures):
        pass

    # Finally, restricting ourselves to finite floats makes the test pass!
    source_code = source_code.replace(
        "st.floats()", "st.floats(allow_nan=False, allow_infinity=False)"
    )
    get_test_function(source_code)()


def test_style_validation():
    ghostwriter._check_style("pytest")
    ghostwriter._check_style("unittest")
    with pytest.raises(InvalidArgument):
        ghostwriter._check_style("not a valid style")


def test_overlapping_args_use_union_of_strategies():
    def f(arg: int) -> None:
        pass

    def g(arg: float) -> None:
        pass

    source_code = ghostwriter.equivalent(f, g)
    assert "arg=st.one_of(st.integers(), st.floats())" in source_code


def test_strategies_with_invalid_syntax_repr_as_nothing():
    msg = "$$ this repr is not Python syntax $$"

    class NoRepr:
        def __repr__(self):
            return msg

    s = just(NoRepr())
    assert repr(s) == f"just({msg})"
    assert ghostwriter._valid_syntax_repr(s) == "nothing()"
