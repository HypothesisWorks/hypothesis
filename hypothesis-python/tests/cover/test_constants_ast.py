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
import inspect
import subprocess
import sys
import textwrap
from types import ModuleType

import pytest

from hypothesis import given, strategies as st
from hypothesis.internal.compat import PYPY
from hypothesis.internal.constants_ast import (
    Constants,
    ConstantVisitor,
    constants_from_module,
    is_local_module_file,
)

from tests.common.utils import skipif_emscripten

constant_ints = st.integers(max_value=-101) | st.integers(min_value=101)
constant_floats = st.floats(allow_nan=False, allow_infinity=False)
constant_bytes = st.binary(min_size=1, max_size=50)
constant_strings = st.text(min_size=1, max_size=10).filter(lambda s: not s.isspace())
constants = constant_ints | constant_floats | constant_bytes | constant_strings

constants_classes = st.builds(
    Constants,
    integers=st.sets(constant_ints),
    floats=st.sets(constant_floats),
    bytes=st.sets(constant_bytes),
    strings=st.sets(constant_strings),
)


def constants_from_ast(tree):
    visitor = ConstantVisitor()
    visitor.visit(tree)
    return visitor.constants


def test_constants_set_from_type_invalid():
    with pytest.raises(ValueError):
        Constants().set_for_type("not_a_type")


@given(st.integers())
def test_constants_contains(n):
    assert n in Constants(integers={n})


@given(constants_classes)
def test_constants_not_equal_to_set(constants):
    assert constants != set()
    assert constants != set(constants)


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
        # * the empty bytestring b""
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
        ("a = b''", set()),
    ],
)
def test_constants_from_ast(source, expected):
    source = textwrap.dedent(source)
    tree = ast.parse(source)
    assert set(constants_from_ast(tree)) == expected


@given(st.integers(max_value=-101))
def test_parses_negatives(n):
    assert constants_from_ast(ast.parse(f"a = {n}")) == Constants(integers={n})


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
    p = tmp_path / "my_constants.py"
    p.write_text(
        textwrap.dedent(
            """
        import sys
        # stdlib
        import json
        # third-party
        import pytest
        import hypothesis
        from hypothesis.internal.constants_ast import (
            is_local_module_file,
            constants_from_module,
            Constants
        )

        # these modules are in fact detected as local if they are installed
        # as editable (as is common for contributors). Prevent the ast constant
        # logic from picking up on them
        for module in sys.modules.copy():
            if module.startswith("hypofuzz"):
                del sys.modules[module]

        constants = Constants()
        for module in sys.modules.values():
            if getattr(module, "__file__", None) is not None and is_local_module_file(
                module.__file__
            ):
                constants |= constants_from_module(module)

        expected = Constants(
            strings={'float', 'string', 'bytes', 'integer', 'test', 'hypofuzz', '__file__'},
            floats={3.14},
            bytes={b'test'},
            integers={142, 101, 102, 103, 104},
        )
        assert constants == expected, set(constants).symmetric_difference(set(expected))

        # local
        a = 142
        b = "test"
        c = True
        d = 3.14
        e = b"test"
        f = (101, 102)
        g = frozenset([103, 104])
        """,
        ),
        encoding="utf-8",
    )
    # this test doubles as a regression test for
    # https://github.com/HypothesisWorks/hypothesis/issues/4375. Fail on comparisons
    # between bytes and str.
    subprocess.check_call([sys.executable, "-bb", str(p)])


def test_constants_from_bad_module():
    # covering test for the except branch
    module = ModuleType("nonexistent")
    assert constants_from_module(module) == Constants()


@pytest.mark.parametrize(
    "path",
    [
        "/path/to/tests/module",
        "/path/to/test/module",
        "/a/test_file.py",
        "/a/file_test.py",
    ],
)
def test_local_modules_ignores_test_modules(path):
    assert not is_local_module_file(path)


@pytest.mark.skipif(PYPY, reason="no memory error on pypy")
def test_ignores_ast_parse_error(tmp_path):
    p = tmp_path / "errors_on_parse.py"
    p.write_text("[1, " * 200 + "]" * 200, encoding="utf-8")
    module = ModuleType("<test_ignores_ast_parse_error>")
    module.__file__ = str(p)

    source = inspect.getsource(module)
    with pytest.raises(MemoryError):
        ast.parse(source)

    assert constants_from_module(module) == Constants()


@given(constants_classes)
def test_constant_visitor_roundtrips_string(constants):
    # our files in storage_directory("constants") rely on this roundtrip
    visitor = ConstantVisitor()
    visitor.visit(ast.parse(str(set(constants))))
    assert visitor.constants == constants
