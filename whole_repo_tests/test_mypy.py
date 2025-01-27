# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import subprocess
import textwrap

import pytest

from hypothesistooling.projects.hypothesispython import PYTHON_SRC
from hypothesistooling.scripts import pip_tool, tool_path

from .revealed_types import NUMPY_REVEALED_TYPES, PYTHON_VERSIONS, REVEALED_TYPES


def test_mypy_passes_on_hypothesis():
    pip_tool("mypy", str(PYTHON_SRC))


@pytest.mark.skip(
    reason="Hypothesis type-annotates the public API as a convenience for users, "
    "but strict checks for our internals would be a net drag on productivity."
)
def test_mypy_passes_on_hypothesis_strict():
    pip_tool("mypy", "--strict", str(PYTHON_SRC))


def get_mypy_output(fname, *extra_args):
    proc = subprocess.run(
        [tool_path("mypy"), "--no-incremental", *extra_args, str(fname)],
        encoding="utf-8",
        capture_output=True,
        text=True,
    )
    if proc.stderr:
        raise AssertionError(f"{proc.returncode=}\n\n{proc.stdout}\n\n{proc.stderr}")
    return proc.stdout


def get_mypy_analysed_type(fname):
    attempts = 0
    while True:
        out = get_mypy_output(fname).rstrip()
        msg = "Success: no issues found in 1 source file"
        if out.endswith(msg):
            out = out[: -len(msg)]
        # we've noticed some flakiness in getting an empty output here. Give it
        # a couple tries.
        if len(out.splitlines()) == 0:
            attempts += 1
            continue

        assert len(out.splitlines()) == 1, out
        assert attempts < 2, "too many failed retries"
        break

    # See https://mypy.readthedocs.io/en/latest/common_issues.html#reveal-type
    # The shell output for `reveal_type([1, 2, 3])` looks like a literal:
    # file.py:2: error: Revealed type is 'builtins.list[builtins.int*]'
    return (
        out.split("Revealed type is ")[1]
        .strip()
        .strip('"' + "'")
        .replace("builtins.", "")
        .replace("*", "")
        .replace(
            "hypothesis.strategies._internal.strategies.SearchStrategy",
            "SearchStrategy",
        )
        .replace("numpy._typing.", "")
        .replace("_nbit_base.", "")
        .replace("numpy.", "")
        .replace("List[", "list[")
        .replace("Dict[", "dict[")
    )


def assert_mypy_errors(fname, expected, python_version=None):
    _args = ["--no-error-summary", "--show-error-codes"]

    if python_version:
        _args.append(f"--python-version={python_version}")

    out = get_mypy_output(fname, *_args)
    del _args
    # Shell output looks like:
    # file.py:2: error: Incompatible types in assignment ... [assignment]

    print(f"mypy output: {out}")

    def convert_lines():
        for error_line in out.splitlines():
            col, category = error_line.split(":")[-3:-1]
            if category.strip() != "error":
                # mypy outputs "note" messages for overload problems, even with
                # --hide-error-context. Don't include these
                continue

            error_code = error_line.split("[")[-1].rstrip("]")
            if error_code == "empty-body":
                continue
            yield (int(col), error_code)

    assert sorted(convert_lines()) == sorted(expected)


@pytest.mark.parametrize(
    "val,expect",
    [
        *REVEALED_TYPES,  # shared with Pyright
        ("lists(none())", "list[None]"),
        ("data()", "hypothesis.strategies._internal.core.DataObject"),
        ("none() | integers()", "Union[None, int]"),
        ("recursive(integers(), lists)", "Union[list[Any], int]"),
        # We have overloads for up to five types, then fall back to Any.
        # (why five?  JSON atoms are None|bool|int|float|str and we do that a lot)
        ("one_of(integers(), text())", "Union[int, str]"),
        (
            "one_of(integers(), text(), none(), binary(), builds(list))",
            "Union[int, str, None, bytes, list[Never]]",
        ),
        (
            "one_of(integers(), text(), none(), binary(), builds(list), builds(dict))",
            "Any",
        ),
        # Note: keep this in sync with the equivalent test for Pyright
    ],
)
def test_revealed_types(tmp_path, val, expect):
    """Check that Mypy picks up the expected `X` in SearchStrategy[`X`]."""
    f = tmp_path / "check.py"
    f.write_text(
        textwrap.dedent(
            f"""
            from hypothesis.strategies import *
            reveal_type({val})
            """
        ),
        encoding="utf-8",
    )
    typ = get_mypy_analysed_type(f)
    assert typ == f"SearchStrategy[{expect}]"


@pytest.mark.parametrize("val,expect", NUMPY_REVEALED_TYPES)
def test_numpy_revealed_types(tmp_path, val, expect):
    f = tmp_path / "check.py"
    f.write_text(
        textwrap.dedent(
            f"""
            import numpy as np
            from hypothesis.extra.numpy import *
            reveal_type({val})
            """
        ),
        encoding="utf-8",
    )
    typ = get_mypy_analysed_type(f)
    assert typ == f"SearchStrategy[{expect}]"


@pytest.mark.parametrize(
    "val,expect",
    [
        ("elements=None, fill=None", "Any"),
        ("elements=None, fill=floats()", "float"),
        ("elements=floats(), fill=None", "float"),
        ("elements=floats(), fill=text()", "object"),
        # Note: keep this in sync with the equivalent test for Mypy
    ],
)
def test_pandas_column(tmp_path, val, expect):
    f = tmp_path / "test.py"
    f.write_text(
        textwrap.dedent(
            f"""
            from hypothesis.extra.pandas import column
            from hypothesis.strategies import floats, text

            x = column(name="test", unique=True, dtype=None, {val})
            reveal_type(x)
            """
        ),
        encoding="utf-8",
    )
    typ = get_mypy_analysed_type(f)
    assert typ == f"hypothesis.extra.pandas.impl.column[{expect}]"


def test_data_object_type_tracing(tmp_path):
    f = tmp_path / "check_mypy_on_st_data.py"
    f.write_text(
        "from hypothesis.strategies import data, integers\n"
        "d = data().example()\n"
        "s = d.draw(integers())\n"
        "reveal_type(s)\n",
        encoding="utf-8",
    )
    got = get_mypy_analysed_type(f)
    assert got == "int"


def test_drawfn_type_tracing(tmp_path):
    f = tmp_path / "check_mypy_on_st_drawfn.py"
    f.write_text(
        "from hypothesis.strategies import DrawFn, text\n"
        "def comp(draw: DrawFn) -> str:\n"
        "    s = draw(text(), 123)\n"
        "    reveal_type(s)\n"
        "    return s\n",
        encoding="utf-8",
    )
    got = get_mypy_analysed_type(f)
    assert got == "str"


def test_composite_type_tracing(tmp_path):
    f = tmp_path / "check_mypy_on_st_composite.py"
    f.write_text(
        "from hypothesis.strategies import composite, DrawFn\n"
        "@composite\n"
        "def comp(draw: DrawFn, x: int) -> int:\n"
        "    return x\n"
        "reveal_type(comp)\n",
        encoding="utf-8",
    )
    got = get_mypy_analysed_type(f)
    assert got == "def (x: int) -> SearchStrategy[int]"


@pytest.mark.parametrize(
    "source, expected",
    [
        ("", "def ()"),
        ("like=f", "def (x: int) -> int"),
        ("returns=booleans()", "def () -> bool"),
        ("like=f, returns=booleans()", "def (x: int) -> bool"),
    ],
)
def test_functions_type_tracing(tmp_path, source, expected):
    f = tmp_path / "check_mypy_on_st_composite.py"
    f.write_text(
        "from hypothesis.strategies import booleans, functions\n"
        "def f(x: int) -> int: return x\n"
        f"g = functions({source}).example()\n"
        "reveal_type(g)\n",
        encoding="utf-8",
    )
    got = get_mypy_analysed_type(f)
    assert got == expected, (got, expected)


def test_settings_preserves_type(tmp_path):
    f = tmp_path / "check_mypy_on_settings.py"
    f.write_text(
        "from hypothesis import settings\n"
        "@settings(max_examples=10)\n"
        "def f(x: int) -> int:\n"
        "    return x\n"
        "reveal_type(f)\n",
        encoding="utf-8",
    )
    got = get_mypy_analysed_type(f)
    assert got == "def (x: int) -> int"


def test_stateful_bundle_generic_type(tmp_path):
    f = tmp_path / "check_mypy_on_stateful_bundle.py"
    f.write_text(
        "from hypothesis.stateful import Bundle\n"
        "b: Bundle[int] = Bundle('test')\n"
        "x = b.example()\n"
        "reveal_type(x)\n",
        encoding="utf-8",
    )
    got = get_mypy_analysed_type(f)
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
def test_stateful_rule_targets(tmp_path, decorator, target_args, returns):
    f = tmp_path / "check_mypy_on_stateful_rule.py"
    f.write_text(
        "from hypothesis.stateful import *\n"
        "b1: Bundle[int] = Bundle('b1')\n"
        "b2: Bundle[int] = Bundle('b2')\n"
        f"@{decorator}({target_args})\n"
        f"def my_rule() -> {returns}:\n"
        "    ...\n",
        encoding="utf-8",
    )
    assert_mypy_errors(f, [])


@pytest.mark.parametrize("decorator", ["rule", "initialize"])
def test_stateful_rule_no_targets(tmp_path, decorator):
    f = tmp_path / "check_mypy_on_stateful_rule.py"
    f.write_text(
        "from hypothesis.stateful import *\n"
        f"@{decorator}()\n"
        "def my_rule() -> None:\n"
        "    ...\n",
        encoding="utf-8",
    )
    assert_mypy_errors(f, [])


@pytest.mark.parametrize("decorator", ["rule", "initialize"])
def test_stateful_target_params_mutually_exclusive(tmp_path, decorator):
    f = tmp_path / "check_mypy_on_stateful_rule.py"
    f.write_text(
        "from hypothesis.stateful import *\n"
        "b1: Bundle[int] = Bundle('b1')\n"
        f"@{decorator}(target=b1, targets=(b1,))\n"
        "def my_rule() -> int:\n"
        "    ...\n",
        encoding="utf-8",
    )
    # Also outputs "misc" error "Untyped decorator makes function "my_rule"
    # untyped, due to the inability to resolve to an appropriate overloaded
    # variant
    assert_mypy_errors(f, [(3, "call-overload"), (3, "misc")])


@pytest.mark.parametrize("decorator", ["rule", "initialize"])
@pytest.mark.parametrize(
    "target_args", ["", "target=b1", "targets=(b1,)", "targets=(b1, b2)"]
)
@pytest.mark.parametrize("returns", ["int", "MultipleResults[int]"])
def test_stateful_target_params_return_type(tmp_path, decorator, target_args, returns):
    f = tmp_path / "check_mypy_on_stateful_rule.py"
    f.write_text(
        "from hypothesis.stateful import *\n"
        "b1: Bundle[str] = Bundle('b1')\n"
        "b2: Bundle[str] = Bundle('b2')\n"
        f"@{decorator}({target_args})\n"
        f"def my_rule() -> {returns}:\n"
        "    ...\n",
        encoding="utf-8",
    )
    assert_mypy_errors(f, [(4, "arg-type")])


@pytest.mark.parametrize("decorator", ["rule", "initialize"])
def test_stateful_no_target_params_return_type(tmp_path, decorator):
    f = tmp_path / "check_mypy_on_stateful_rule.py"
    f.write_text(
        "from hypothesis.stateful import *\n"
        f"@{decorator}()\n"
        "def my_rule() -> int:\n"
        "    ...\n",
        encoding="utf-8",
    )
    assert_mypy_errors(f, [(2, "arg-type")])


@pytest.mark.parametrize("decorator", ["rule", "initialize"])
@pytest.mark.parametrize("use_multi", [True, False])
def test_stateful_bundle_variance(tmp_path, decorator, use_multi):
    f = tmp_path / "check_mypy_on_stateful_bundle.py"
    if use_multi:
        return_type = "MultipleResults[Dog]"
        return_expr = "multiple(dog, dog)"
    else:
        return_type = "Dog"
        return_expr = "dog"

    f.write_text(
        "from hypothesis.stateful import *\n"
        "class Animal: pass\n"
        "class Dog(Animal): pass\n"
        "a: Bundle[Animal] = Bundle('animal')\n"
        "d: Bundle[Dog] = Bundle('dog')\n"
        f"@{decorator}(target=a, dog=d)\n"
        f"def my_rule(dog: Dog) -> {return_type}:\n"
        f"    return {return_expr}\n",
        encoding="utf-8",
    )
    assert_mypy_errors(f, [])


@pytest.mark.parametrize("decorator", ["rule", "initialize"])
def test_stateful_multiple_return(tmp_path, decorator):
    f = tmp_path / "check_mypy_on_stateful_multiple.py"
    f.write_text(
        "from hypothesis.stateful import *\n"
        "b: Bundle[int] = Bundle('b')\n"
        f"@{decorator}(target=b)\n"
        "def my_rule() -> MultipleResults[int]:\n"
        "    return multiple(1, 2, 3)\n",
        encoding="utf-8",
    )
    assert_mypy_errors(f, [])


@pytest.mark.parametrize("decorator", ["rule", "initialize"])
def test_stateful_multiple_return_invalid(tmp_path, decorator):
    f = tmp_path / "check_mypy_on_stateful_multiple.py"
    f.write_text(
        "from hypothesis.stateful import *\n"
        "b: Bundle[str] = Bundle('b')\n"
        f"@{decorator}(target=b)\n"
        "def my_rule() -> MultipleResults[int]:\n"
        "    return multiple(1, 2, 3)\n",
        encoding="utf-8",
    )
    assert_mypy_errors(f, [(3, "arg-type")])


@pytest.mark.parametrize(
    "wrapper,expected",
    [
        ("{}", "int"),
        ("st.lists({})", "list[int]"),
    ],
)
def test_stateful_consumes_type_tracing(tmp_path, wrapper, expected):
    f = tmp_path / "check_mypy_on_stateful_rule.py"
    wrapped = wrapper.format("consumes(b)")
    f.write_text(
        "from hypothesis.stateful import *\n"
        "from hypothesis import strategies as st\n"
        "b: Bundle[int] = Bundle('b')\n"
        f"s = {wrapped}\n"
        "reveal_type(s.example())\n",
        encoding="utf-8",
    )
    got = get_mypy_analysed_type(f)
    assert got == expected


def test_stateful_consumed_bundle_cannot_be_target(tmp_path):
    f = tmp_path / "check_mypy_on_stateful_rule.py"
    f.write_text(
        "from hypothesis.stateful import *\n"
        "b: Bundle[int] = Bundle('b')\n"
        "rule(target=consumes(b))\n",
        encoding="utf-8",
    )
    assert_mypy_errors(f, [(3, "call-overload")])


@pytest.mark.parametrize(
    "return_val,errors",
    [
        ("True", []),
        ("0", [(2, "arg-type"), (2, "return-value")]),
    ],
)
def test_stateful_precondition_requires_predicate(tmp_path, return_val, errors):
    f = tmp_path / "check_mypy_on_stateful_precondition.py"
    f.write_text(
        "from hypothesis.stateful import *\n"
        f"@precondition(lambda self: {return_val})\n"
        "def my_rule() -> None: ...\n",
        encoding="utf-8",
    )
    assert_mypy_errors(f, errors)


def test_stateful_precondition_lambda(tmp_path):
    f = tmp_path / "check_mypy_on_stateful_precondition.py"
    f.write_text(
        "from hypothesis.stateful import *\n"
        "class MyMachine(RuleBasedStateMachine):\n"
        "  valid: bool\n"
        "  @precondition(lambda self: self.valid)\n"
        "  @rule()\n"
        "  def my_rule(self) -> None: ...\n",
        encoding="utf-8",
    )
    # Note that this doesn't fully check the code because of the `Any` parameter
    # type. `lambda self: self.invalid` would unfortunately pass too
    assert_mypy_errors(f, [])


def test_stateful_precondition_instance_method(tmp_path):
    f = tmp_path / "check_mypy_on_stateful_precondition.py"
    f.write_text(
        "from hypothesis.stateful import *\n"
        "class MyMachine(RuleBasedStateMachine):\n"
        "  valid: bool\n"
        "  def check(self) -> bool:\n"
        "    return self.valid\n"
        "  @precondition(check)\n"
        "  @rule()\n"
        "  def my_rule(self) -> None: ...\n",
        encoding="utf-8",
    )
    assert_mypy_errors(f, [])


def test_stateful_precondition_precond_requires_one_arg(tmp_path):
    f = tmp_path / "check_mypy_on_stateful_precondition.py"
    f.write_text(
        "from hypothesis.stateful import *\n"
        "precondition(lambda: True)\n"
        "precondition(lambda a, b: True)\n",
        encoding="utf-8",
    )
    # Additional "Cannot infer type of lambda" errors
    assert_mypy_errors(
        f,
        [(2, "arg-type"), (2, "misc"), (3, "arg-type"), (3, "misc")],
    )


def test_pos_only_args(tmp_path):
    f = tmp_path / "check_mypy_on_pos_arg_only_strats.py"
    f.write_text(
        textwrap.dedent(
            """
            import hypothesis.strategies as st

            st.tuples(a1=st.integers())
            st.tuples(a1=st.integers(), a2=st.integers())

            st.one_of(a1=st.integers())
            st.one_of(a1=st.integers(), a2=st.integers())
            """
        ),
        encoding="utf-8",
    )
    assert_mypy_errors(
        f,
        [
            (4, "call-overload"),
            (5, "call-overload"),
            (7, "call-overload"),
            (8, "call-overload"),
        ],
    )


@pytest.mark.parametrize("python_version", PYTHON_VERSIONS)
def test_mypy_passes_on_basic_test(tmp_path, python_version):
    f = tmp_path / "check_mypy_on_basic_tests.py"
    f.write_text(
        textwrap.dedent(
            """
            import hypothesis
            import hypothesis.strategies as st

            @hypothesis.given(x=st.text())
            def test_foo(x: str) -> None:
                assert x == x

            from hypothesis import given
            from hypothesis.strategies import text

            @given(x=text())
            def test_bar(x: str) -> None:
                assert x == x
            """
        ),
        encoding="utf-8",
    )
    assert_mypy_errors(f, [], python_version=python_version)


@pytest.mark.parametrize("python_version", PYTHON_VERSIONS)
def test_given_only_allows_strategies(tmp_path, python_version):
    f = tmp_path / "check_mypy_given_expects_strategies.py"
    f.write_text(
        textwrap.dedent(
            """
            from hypothesis import given

            @given(1)
            def f():
                pass
            """
        ),
        encoding="utf-8",
    )
    assert_mypy_errors(f, [(4, "call-overload")], python_version=python_version)


@pytest.mark.parametrize("python_version", PYTHON_VERSIONS)
def test_raises_for_mixed_pos_kwargs_in_given(tmp_path, python_version):
    f = tmp_path / "raises_for_mixed_pos_kwargs_in_given.py"
    f.write_text(
        textwrap.dedent(
            """
            from hypothesis import given
            from hypothesis.strategies import text

            @given(text(), x=text())
            def test_bar(x):
                ...
            """
        ),
        encoding="utf-8",
    )
    assert_mypy_errors(f, [(5, "call-overload")], python_version=python_version)


def test_register_random_interface(tmp_path):
    f = tmp_path / "check_mypy_on_pos_arg_only_strats.py"
    f.write_text(
        textwrap.dedent(
            """
            from random import Random
            from hypothesis import register_random

            class MyRandom:
                def __init__(self) -> None:
                    r = Random()
                    self.seed = r.seed
                    self.setstate = r.setstate
                    self.getstate = r.getstate

            register_random(MyRandom())
            register_random(None)  # type: ignore[arg-type]
            """
        ),
        encoding="utf-8",
    )
    assert_mypy_errors(f, [])
