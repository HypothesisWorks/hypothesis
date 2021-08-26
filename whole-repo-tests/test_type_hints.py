# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
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

import os
import subprocess

import pytest
from hypothesistooling.projects.hypothesispython import PYTHON_SRC
from hypothesistooling.scripts import pip_tool, tool_path


def test_mypy_passes_on_hypothesis():
    pip_tool("mypy", PYTHON_SRC)


def get_mypy_analysed_type(fname, val):
    out = subprocess.Popen(
        [tool_path("mypy"), fname],
        stdout=subprocess.PIPE,
        encoding="utf-8",
        universal_newlines=True,
        # We set the MYPYPATH explicitly, because PEP561 discovery wasn't
        # working in CI as of mypy==0.730 - hopefully a temporary workaround.
        env=dict(os.environ, MYPYPATH=PYTHON_SRC),
    ).stdout.read()
    assert len(out.splitlines()) == 1
    # See https://mypy.readthedocs.io/en/latest/common_issues.html#reveal-type
    # The shell output for `reveal_type([1, 2, 3])` looks like a literal:
    # file.py:2: error: Revealed type is 'builtins.list[builtins.int*]'
    return (
        out.split("Revealed type is ")[1]
        .strip()
        .strip('"' + "'")
        .replace("builtins.", "")
        .replace("*", "")
    )


@pytest.mark.parametrize(
    "val,expect",
    [
        ("integers()", "int"),
        ("text()", "str"),
        ("integers().map(str)", "str"),
        ("booleans().filter(bool)", "bool"),
        ("lists(none())", "list[None]"),
        ("dictionaries(integers(), datetimes())", "dict[int, datetime.datetime]"),
        ("data()", "hypothesis.strategies._internal.core.DataObject"),
        ("none() | integers()", "Union[None, int]"),
        # Ex`-1 stands for recursion in the whole type, i.e. Ex`0 == Union[...]
        ("recursive(integers(), lists)", "Union[list[Ex`-1], int]"),
        # We have overloads for up to five types, then fall back to Any.
        # (why five?  JSON atoms are None|bool|int|float|str and we do that a lot)
        ("one_of(integers(), text())", "Union[int, str]"),
        (
            "one_of(integers(), text(), none(), binary(), builds(list))",
            "Union[int, str, None, bytes, list[_T`1]]",
        ),
        (
            "one_of(integers(), text(), none(), binary(), builds(list), builds(dict))",
            "Any",
        ),
        ("tuples()", "Tuple[]"),  # Should be `Tuple[()]`, but this is what mypy prints
        ("tuples(integers())", "Tuple[int]"),
        ("tuples(integers(), text())", "Tuple[int, str]"),
        (
            "tuples(integers(), text(), integers(), text(), integers())",
            "Tuple[int, str, int, str, int]",
        ),
        (
            "tuples(text(), text(), text(), text(), text(), text())",
            "tuple[Any]",  # note lower-case; this is the arbitrary-length *args case
        ),
    ],
)
def test_revealed_types(tmpdir, val, expect):
    """Check that Mypy picks up the expected `X` in SearchStrategy[`X`]."""
    f = tmpdir.join(expect + ".py")
    f.write(
        "from hypothesis.strategies import *\n"
        "s = {}\n"
        "reveal_type(s)\n".format(val)
    )
    typ = get_mypy_analysed_type(str(f.realpath()), val)
    assert typ == f"hypothesis.strategies._internal.strategies.SearchStrategy[{expect}]"


def test_data_object_type_tracing(tmpdir):
    f = tmpdir.join("check_mypy_on_st_data.py")
    f.write(
        "from hypothesis.strategies import data, integers\n"
        "d = data().example()\n"
        "s = d.draw(integers())\n"
        "reveal_type(s)\n"
    )
    got = get_mypy_analysed_type(str(f.realpath()), "data().draw(integers())")
    assert got == "int"


def test_drawfn_type_tracing(tmpdir):
    f = tmpdir.join("check_mypy_on_st_drawfn.py")
    f.write(
        "from hypothesis.strategies import DrawFn, text\n"
        "def comp(draw: DrawFn) -> str:\n"
        "    s = draw(text(), 123)\n"
        "    reveal_type(s)\n"
        "    return s\n"
    )
    got = get_mypy_analysed_type(str(f.realpath()), ...)
    assert got == "str"


def test_settings_preserves_type(tmpdir):
    f = tmpdir.join("check_mypy_on_settings.py")
    f.write(
        "from hypothesis import settings\n"
        "@settings(max_examples=10)\n"
        "def f(x: int) -> int:\n"
        "    return x\n"
        "reveal_type(f)\n"
    )
    got = get_mypy_analysed_type(str(f.realpath()), ...)
    assert got == "def (x: int) -> int"
