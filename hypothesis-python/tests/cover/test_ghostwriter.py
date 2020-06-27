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
from decimal import Decimal
from typing import List, Sequence, Set

import pytest

from hypothesis import ghostwriter
from hypothesis.errors import InvalidArgument

varied_excepts = pytest.mark.parametrize("ex", [(), ValueError, (TypeError, re.error)])


def get_test_function(source_code):
    # A helper function to get the dynamically-defined test function.
    # Note that this also tests that the module is syntatically-valid,
    # AND free from undefined names, import problems, and so on.
    namespace = {}
    exec(source_code, namespace)
    tests = [v for k, v in namespace.items() if k.startswith(("test_", "Test"))]
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


def no_annotations(foo=None, bar=False):
    pass


def test_inference_from_defaults_and_none_booleans_reprs_not_just_and_sampled_from():
    source_code = ghostwriter.fuzz(no_annotations)
    assert "@given(foo=st.none(), bar=st.booleans())" in source_code


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


@pytest.mark.parametrize("gw,args", [(ghostwriter.fuzz, ["not callable"])])
def test_invalid_func_inputs(gw, args):
    with pytest.raises(InvalidArgument):
        gw(*args)
