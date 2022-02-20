# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import os
import subprocess

import pytest

from hypothesistooling.projects.hypothesispython import PYTHON_SRC
from hypothesistooling.scripts import pip_tool, tool_path


def test_mypy_passes_on_hypothesis():
    pip_tool("mypy", PYTHON_SRC)


def get_mypy_output(fname, *extra_args):
    return subprocess.Popen(
        [tool_path("mypy"), *extra_args, fname],
        stdout=subprocess.PIPE,
        encoding="utf-8",
        universal_newlines=True,
        # We set the MYPYPATH explicitly, because PEP561 discovery wasn't
        # working in CI as of mypy==0.730 - hopefully a temporary workaround.
        env=dict(os.environ, MYPYPATH=PYTHON_SRC),
    ).stdout.read()


def get_mypy_analysed_type(fname, val):
    out = get_mypy_output(fname)
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


def assert_mypy_errors(fname, expected):
    out = get_mypy_output(fname, "--no-error-summary", "--show-error-codes")
    # Shell output looks like:
    # file.py:2: error: Incompatible types in assignment ... [assignment]

    def convert_lines():
        for error_line in out.splitlines():
            col, category = error_line.split(":")[1:3]
            if category.strip() != "error":
                # mypy outputs "note" messages for overload problems, even with
                # --hide-error-context. Don't include these
                continue

            # Intentional print so we can check mypy's output if a test fails
            print(error_line)
            error_code = error_line.split("[")[-1].rstrip("]")
            yield (int(col), error_code)

    assert sorted(convert_lines()) == sorted(expected)


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
        f"s = {val}\n"
        "reveal_type(s)\n"  # fmt: skip
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


def test_stateful_bundle_generic_type(tmpdir):
    f = tmpdir.join("check_mypy_on_stateful_bundle.py")
    f.write(
        "from hypothesis.stateful import Bundle\n"
        "b: Bundle[int] = Bundle('test')\n"
        "reveal_type(b.example())\n"
    )
    got = get_mypy_analysed_type(str(f.realpath()), ...)
    assert got == "int"


@pytest.mark.parametrize("decorator", ["rule", "initialize"])
@pytest.mark.parametrize(
    "target_args",
    [
        "target=b1",
        "targets=(b1,)",
        "targets=(b1, b2)",
    ],
)
@pytest.mark.parametrize("returns", ["int", "MultipleResults[int]"])
def test_stateful_rule_targets(tmpdir, decorator, target_args, returns):
    f = tmpdir.join("check_mypy_on_stateful_rule.py")
    f.write(
        "from hypothesis.stateful import *\n"
        "b1: Bundle[int] = Bundle('b1')\n"
        "b2: Bundle[int] = Bundle('b2')\n"
        f"@{decorator}({target_args})\n"
        f"def my_rule() -> {returns}:\n"
        "    ...\n"
    )
    assert_mypy_errors(str(f.realpath()), [])


@pytest.mark.parametrize("decorator", ["rule", "initialize"])
def test_stateful_rule_no_targets(tmpdir, decorator):
    f = tmpdir.join("check_mypy_on_stateful_rule.py")
    f.write(
        "from hypothesis.stateful import *\n"
        f"@{decorator}()\n"
        "def my_rule() -> None:\n"
        "    ...\n"
    )
    assert_mypy_errors(str(f.realpath()), [])


@pytest.mark.parametrize("decorator", ["rule", "initialize"])
def test_stateful_target_params_mutually_exclusive(tmpdir, decorator):
    f = tmpdir.join("check_mypy_on_stateful_rule.py")
    f.write(
        "from hypothesis.stateful import *\n"
        "b1: Bundle[int] = Bundle('b1')\n"
        f"@{decorator}(target=b1, targets=(b1,))\n"
        "def my_rule() -> int:\n"
        "    ...\n"
    )
    # Also outputs "misc" error "Untyped decorator makes function "my_rule"
    # untyped, due to the inability to resolve to an appropriate overloaded
    # variant
    assert_mypy_errors(str(f.realpath()), [(3, "call-overload"), (3, "misc")])


@pytest.mark.parametrize("decorator", ["rule", "initialize"])
@pytest.mark.parametrize(
    "target_args",
    [
        "target=b1",
        "targets=(b1,)",
        "targets=(b1, b2)",
        "",
    ],
)
@pytest.mark.parametrize("returns", ["int", "MultipleResults[int]"])
def test_stateful_target_params_return_type(tmpdir, decorator, target_args, returns):
    f = tmpdir.join("check_mypy_on_stateful_rule.py")
    f.write(
        "from hypothesis.stateful import *\n"
        "b1: Bundle[str] = Bundle('b1')\n"
        "b2: Bundle[str] = Bundle('b2')\n"
        f"@{decorator}({target_args})\n"
        f"def my_rule() -> {returns}:\n"
        "    ...\n"
    )
    assert_mypy_errors(str(f.realpath()), [(4, "arg-type")])


@pytest.mark.parametrize("decorator", ["rule", "initialize"])
def test_stateful_no_target_params_return_type(tmpdir, decorator):
    f = tmpdir.join("check_mypy_on_stateful_rule.py")
    f.write(
        "from hypothesis.stateful import *\n"
        f"@{decorator}()\n"
        "def my_rule() -> int:\n"
        "    ...\n"
    )
    assert_mypy_errors(str(f.realpath()), [(2, "arg-type")])


@pytest.mark.parametrize("decorator", ["rule", "initialize"])
@pytest.mark.parametrize("use_multi", [True, False])
def test_stateful_bundle_variance(tmpdir, decorator, use_multi):
    f = tmpdir.join("check_mypy_on_stateful_bundle.py")
    if use_multi:
        return_type = "MultipleResults[Dog]"
        return_expr = "multiple(dog, dog)"
    else:
        return_type = "Dog"
        return_expr = "dog"

    f.write(
        "from hypothesis.stateful import *\n"
        "class Animal: pass\n"
        "class Dog(Animal): pass\n"
        "a: Bundle[Animal] = Bundle('animal')\n"
        "d: Bundle[Dog] = Bundle('dog')\n"
        f"@{decorator}(target=a, dog=d)\n"
        f"def my_rule(dog: Dog) -> {return_type}:\n"
        f"    return {return_expr}\n"
    )
    assert_mypy_errors(str(f.realpath()), [])


@pytest.mark.parametrize("decorator", ["rule", "initialize"])
def test_stateful_multiple_return(tmpdir, decorator):
    f = tmpdir.join("check_mypy_on_stateful_multiple.py")
    f.write(
        "from hypothesis.stateful import *\n"
        "b: Bundle[int] = Bundle('b')\n"
        f"@{decorator}(target=b)\n"
        "def my_rule() -> MultipleResults[int]:\n"
        "    return multiple(1, 2, 3)\n"
    )
    assert_mypy_errors(str(f.realpath()), [])


@pytest.mark.parametrize("decorator", ["rule", "initialize"])
def test_stateful_multiple_return_invalid(tmpdir, decorator):
    f = tmpdir.join("check_mypy_on_stateful_multiple.py")
    f.write(
        "from hypothesis.stateful import *\n"
        "b: Bundle[str] = Bundle('b')\n"
        f"@{decorator}(target=b)\n"
        "def my_rule() -> MultipleResults[int]:\n"
        "    return multiple(1, 2, 3)\n"
    )
    assert_mypy_errors(str(f.realpath()), [(3, "arg-type")])


@pytest.mark.parametrize(
    "wrapper,expected",
    [
        ("{}", "int"),
        ("st.lists({})", "list[int]"),
    ],
)
def test_stateful_consumes_type_tracing(tmpdir, wrapper, expected):
    f = tmpdir.join("check_mypy_on_stateful_rule.py")
    wrapped = wrapper.format("consumes(b)")
    f.write(
        "from hypothesis.stateful import *\n"
        "from hypothesis import strategies as st\n"
        "b: Bundle[int] = Bundle('b')\n"
        f"s = {wrapped}\n"
        "reveal_type(s.example())\n"
    )
    got = get_mypy_analysed_type(str(f.realpath()), ...)
    assert got == expected


def test_stateful_consumed_bundle_cannot_be_target(tmpdir):
    f = tmpdir.join("check_mypy_on_stateful_rule.py")
    f.write(
        "from hypothesis.stateful import *\n"
        "b: Bundle[int] = Bundle('b')\n"
        "rule(target=consumes(b))\n"
    )
    assert_mypy_errors(str(f.realpath()), [(3, "call-overload")])


@pytest.mark.parametrize(
    "return_val,errors",
    [
        ("True", []),
        ("0", [(2, "arg-type"), (2, "return-value")]),
    ],
)
def test_stateful_precondition_requires_predicate(tmpdir, return_val, errors):
    f = tmpdir.join("check_mypy_on_stateful_precondition.py")
    f.write(
        "from hypothesis.stateful import *\n"
        f"@precondition(lambda self: {return_val})\n"
        "def my_rule() -> None: ...\n"
    )
    assert_mypy_errors(str(f.realpath()), errors)


def test_stateful_precondition_lambda(tmpdir):
    f = tmpdir.join("check_mypy_on_stateful_precondition.py")
    f.write(
        "from hypothesis.stateful import *\n"
        "class MyMachine(RuleBasedStateMachine):\n"
        "  valid: bool\n"
        "  @precondition(lambda self: self.valid)\n"
        "  @rule()\n"
        "  def my_rule(self) -> None: ...\n"
    )
    # Note that this doesn't fully check the code because of the `Any` parameter
    # type. `lambda self: self.invalid` would unfortunately pass too
    assert_mypy_errors(str(f.realpath()), [])


def test_stateful_precondition_instance_method(tmpdir):
    f = tmpdir.join("check_mypy_on_stateful_precondition.py")
    f.write(
        "from hypothesis.stateful import *\n"
        "class MyMachine(RuleBasedStateMachine):\n"
        "  valid: bool\n"
        "  def check(self) -> bool:\n"
        "    return self.valid\n"
        "  @precondition(check)\n"
        "  @rule()\n"
        "  def my_rule(self) -> None: ...\n"
    )
    assert_mypy_errors(str(f.realpath()), [])


def test_stateful_precondition_precond_requires_one_arg(tmpdir):
    f = tmpdir.join("check_mypy_on_stateful_precondition.py")
    f.write(
        "from hypothesis.stateful import *\n"
        "precondition(lambda: True)\n"
        "precondition(lambda a, b: True)\n"
    )
    # Additional "Cannot infer type of lambda" errors
    assert_mypy_errors(
        str(f.realpath()),
        [(2, "arg-type"), (2, "misc"), (3, "arg-type"), (3, "misc")],
    )
