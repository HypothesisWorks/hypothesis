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


@pytest.mark.parametrize(
    "source, expected",
    [
        (
            """
            a1 = 42
            a2 = 3.14
            a3 = 'test1'
            a4 = b'test2'
            a5 = (1, 2)
            a6 = frozenset([3])
            """,
            {42, 3.14, "test1", b"test2", 1, 2, 3},
        ),
        ("a = (1, (2, 3), frozenset([4, 5]))", {1, 2, 3, 4, 5}),
        ("a = {'b': 1}", {"b", 1}),
        ("a = [1]", {1}),
        ("a = +42", {42}),
        ("a = 1 + 2", {1, 2}),
        ("a = ~ 42", {42}),
        # the following cases are ignored:
        # * booleans
        # * f-strings
        # * long strings
        # * pure-whitespace strings
        # * math.inf and math.nan (not constants, but we don't want to collect them
        #   even if they were)
        ("a = True", set()),
        ("a = False", set()),
        ("a = not False", set()),
        ('a = f"test {x}"', set()),
        (f'a = "{"b" * 100}"', set()),
        ('a = ""', set()),
        ('a = " "', set()),
        ('a = "\\n    \\n  \\n"', set()),
        ("a = 1e999", set()),
        ("a = math.inf", set()),
        ("a = math.nan", set()),
    ],
)
def test_constants_from_ast(source, expected):
    source = textwrap.dedent(source)
    tree = ast.parse(source)
    assert constants_from_ast(tree) == expected


@given(st.integers(max_value=-1))
def test_parses_negatives(n):
    assert constants_from_ast(ast.parse(f"a = {n}")) == {n}


constants = st.one_of(
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.binary(),
    # constants_from_ast ignores the following strings:
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
        a = 42
        b = "test1"
        c = True
        d = 3.14
        e = b"test2"
        f = (1, 2)
        g = frozenset([3, 4])
        actual = local_constants()
        assert actual == {
            "hypofuzz",
            42,
            "test1",
            True,
            3.14,
            b"test2",
            1,
            2,
            3,
            4
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
