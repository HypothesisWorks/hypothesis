# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import ast
import subprocess
import sys
import textwrap
from types import ModuleType

import pytest

from hypothesis import given, strategies as st
from hypothesis.internal.constants_ast import _module_ast, constants_from_ast

from tests.common.utils import skipif_emscripten


@pytest.mark.parametrize(
    "source, expected",
    [
        (
            """
            a1 = 142
            a2 = 3.14
            a3 = 'test1'
            a4 = b'test2'
            a5 = (101, 102)
            a6 = frozenset([103])
            """,
            {142, 3.14, 101, 102, 103, "test1", b"test2"},
        ),
        (
            "a = (101, (102, 103), frozenset([104, 105]))",
            {101, 102, 103, 104, 105},
        ),
        ("a = {'b': 101}", {"b", 101}),
        ("a = [101]", {101}),
        ("a = +142", {142}),
        ("a = 101 + 102", {101, 102}),
        ("a = ~ 142", {142}),
        # the following cases are ignored:
        # * booleans
        # * math.inf and math.nan (not constants, but we don't want to collect them
        #   even if they were)
        # * f-strings
        # * long strings
        # * pure-whitespace strings
        # * standalone string expressions (strings not assigned to a variable).
        #   This covers docstrings of all kinds.
        # * small integers
        ("a = True", set()),
        ("a = False", set()),
        ("a = not False", set()),
        ("a = 1e999", set()),
        ("a = math.inf", set()),
        ("a = math.nan", set()),
        ('a = f"test {x}"', set()),
        (f'a = "{"b" * 100}"', set()),
        ('a = ""', set()),
        ('a = " "', set()),
        ('a = "\\n    \\n  \\n"', set()),
        ("'test'", set()),
        ("'test with \\n newlines'", set()),
        ("a = 10", set()),
        ("a = -1", set()),
    ],
)
def test_constants_from_ast(source, expected):
    source = textwrap.dedent(source)
    tree = ast.parse(source)
    assert constants_from_ast(tree) == expected


@given(st.integers(max_value=-101))
def test_parses_negatives(n):
    assert constants_from_ast(ast.parse(f"a = {n}")) == {n}


constants = st.one_of(
    # constants_from_ast skips small integers
    st.integers(max_value=-101),
    st.integers(min_value=101),
    st.floats(allow_nan=False, allow_infinity=False),
    st.binary(),
    # constants_from_ast skips the following strings:
    # * empty strings
    # * long strings
    # * strings which are entirely spaces
    st.text(min_size=1, max_size=10).filter(lambda s: not s.isspace()),
)


@given(st.tuples(constants))
def test_tuple_constants(value):
    tree = ast.parse(str(value))
    assert set(constants_from_ast(tree)) == set(value)


@given(st.frozensets(constants))
def test_frozenset_constants(value):
    tree = ast.parse(str(value))
    assert set(constants_from_ast(tree)) == set(value)


@skipif_emscripten
def test_constants_from_running_file(tmp_path):
    p = tmp_path / "test_constants.py"
    p.write_text(
        textwrap.dedent(
            """
        import sys
        # stdlib
        import json
        # third-party
        import pytest
        import hypothesis
        from hypothesis.internal.constants_ast import local_constants

        # these modules are in fact detected as local if they are installed
        # as editable (as is common for contributors). Prevent the ast constant
        # logic from picking up on them
        for module in sys.modules.copy():
            if module.startswith("hypofuzz"):
                del sys.modules[module]

        # local
        a = 142
        b = "test1"
        c = True
        d = 3.14
        e = b"test2"
        f = (101, 102)
        g = frozenset([103, 104])
        actual = local_constants()
        assert actual == {
            'string': {'float', 'string', 'bytes', 'integer', 'test1', 'hypofuzz'},
            'float': {3.14},
            'bytes': {b'test2'},
            "integer": {142, 101, 102, 103, 104}
        }, actual
        """,
        ),
        encoding="utf-8",
    )
    subprocess.check_call([sys.executable, str(p)])


def test_constants_from_bad_module():
    # covering test for the except branch
    module = ModuleType("nonexistent")
    assert _module_ast(module) is None
