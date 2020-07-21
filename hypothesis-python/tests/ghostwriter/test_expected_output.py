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

To update the recorded outputs, simply run the tests with the
"GHOSTWRITER_UPDATE" environment variable set.
"""

import ast
import json
import os
import re
from typing import Sequence

import pytest

from hypothesis.extra import ghostwriter


def timsort(seq: Sequence[int]) -> Sequence[int]:
    return sorted(seq)


# Note: for some of the `expected` outputs, we replace away some small
#       parts which vary between minor versions of Python.
@pytest.mark.parametrize(
    "data",
    [
        ("RE_COMPILE", ghostwriter.fuzz(re.compile)),
        (
            "RE_COMPILE_EXCEPT",
            ghostwriter.fuzz(re.compile, except_=re.error)
            # re.error fixed it's __module__ in Python 3.7
            .replace("import sre_constants\n", "").replace("sre_constants.", "re."),
        ),
        ("SORTED_IDEMPOTENT", ghostwriter.idempotent(sorted)),
        ("TIMSORT_IDEMPOTENT", ghostwriter.idempotent(timsort)),
        ("EVAL_EQUIVALENT", ghostwriter.equivalent(eval, ast.literal_eval)),
        (
            "JSON_ROUNTTRIP",
            ghostwriter.roundtrip(json.dumps, json.loads)
            # deprecated since 3.1; removed in 3.8+
            .replace("    encoding=st.none(),\n", "")
            .replace("    encoding,\n", "")
            .replace("        encoding=encoding,\n", ""),
        ),
    ],
    ids=lambda x: x[0],
)
def test_ghostwriter_example_outputs(data):
    name, actual = data
    expected = globals()[name][1:]  # remove leading newline
    if "GHOSTWRITER_UPDATE" in os.environ:
        print("Updating", name)
        with open(__file__) as f:
            lines = f.readlines()
        start = lines.index(name + ' = """\n')
        end = lines.index('"""\n', start)
        lines[start + 1 : end] = actual.splitlines(keepends=True)
        with open(__file__, mode="w") as f:
            f.writelines(lines)
    else:
        assert actual == expected  # We got the expected source code
        exec(expected)  # and without any SyntaxError or NameError


RE_COMPILE = """
# This test code was written by the `hypothesis.extra.ghostwriter` module
# and is provided under the Creative Commons Zero public domain dedication.
import re

from hypothesis import given, strategies as st


# TODO: replace st.nothing() with an appropriate strategy


@given(pattern=st.nothing(), flags=st.just(0))
def test_fuzz_compile(pattern, flags):
    re.compile(pattern=pattern, flags=flags)
"""

RE_COMPILE_EXCEPT = """
# This test code was written by the `hypothesis.extra.ghostwriter` module
# and is provided under the Creative Commons Zero public domain dedication.
import re

from hypothesis import given, reject, strategies as st


# TODO: replace st.nothing() with an appropriate strategy


@given(pattern=st.nothing(), flags=st.just(0))
def test_fuzz_compile(pattern, flags):
    try:
        re.compile(pattern=pattern, flags=flags)
    except re.error:
        reject()
"""

SORTED_IDEMPOTENT = """
# This test code was written by the `hypothesis.extra.ghostwriter` module
# and is provided under the Creative Commons Zero public domain dedication.


from hypothesis import given, strategies as st


# TODO: replace st.nothing() with an appropriate strategy


@given(iterable=st.nothing(), key=st.none(), reverse=st.booleans())
def test_idempotent_sorted(iterable, key, reverse):
    result = sorted(iterable, key=key, reverse=reverse)
    repeat = sorted(result, key=key, reverse=reverse)
    assert result == repeat, (result, repeat)
"""

TIMSORT_IDEMPOTENT = """
# This test code was written by the `hypothesis.extra.ghostwriter` module
# and is provided under the Creative Commons Zero public domain dedication.
import test_expected_output

from hypothesis import given, strategies as st


@given(seq=st.one_of(st.binary(), st.binary().map(bytearray), st.lists(st.integers())))
def test_idempotent_timsort(seq):
    result = test_expected_output.timsort(seq=seq)
    repeat = test_expected_output.timsort(seq=result)
    assert result == repeat, (result, repeat)
"""

EVAL_EQUIVALENT = """
# This test code was written by the `hypothesis.extra.ghostwriter` module
# and is provided under the Creative Commons Zero public domain dedication.
import ast

from hypothesis import given, strategies as st


# TODO: replace st.nothing() with an appropriate strategy


@given(
    globals=st.none(),
    locals=st.none(),
    source=st.nothing(),
    node_or_string=st.nothing(),
)
def test_equivalent_eval_literal_eval(globals, locals, source, node_or_string):
    result_eval = eval(source, globals, locals)
    result_literal_eval = ast.literal_eval(node_or_string=node_or_string)
    assert result_eval == result_literal_eval, (result_eval, result_literal_eval)
"""

JSON_ROUNTTRIP = """
# This test code was written by the `hypothesis.extra.ghostwriter` module
# and is provided under the Creative Commons Zero public domain dedication.
import json

from hypothesis import given, strategies as st


# TODO: replace st.nothing() with an appropriate strategy


@given(
    allow_nan=st.booleans(),
    check_circular=st.booleans(),
    cls=st.none(),
    default=st.none(),
    ensure_ascii=st.booleans(),
    indent=st.none(),
    obj=st.nothing(),
    separators=st.none(),
    skipkeys=st.booleans(),
    sort_keys=st.booleans(),
    object_hook=st.none(),
    object_pairs_hook=st.none(),
    parse_constant=st.none(),
    parse_float=st.none(),
    parse_int=st.none(),
)
def test_roundtrip_dumps_loads(
    allow_nan,
    check_circular,
    cls,
    default,
    ensure_ascii,
    indent,
    obj,
    separators,
    skipkeys,
    sort_keys,
    object_hook,
    object_pairs_hook,
    parse_constant,
    parse_float,
    parse_int,
):
    value0 = json.dumps(
        obj=obj,
        skipkeys=skipkeys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        cls=cls,
        indent=indent,
        separators=separators,
        default=default,
        sort_keys=sort_keys,
    )
    value1 = json.loads(
        s=value0,
        cls=cls,
        object_hook=object_hook,
        parse_float=parse_float,
        parse_int=parse_int,
        parse_constant=parse_constant,
        object_pairs_hook=object_pairs_hook,
    )
    assert obj == value1, (obj, value1)
"""
