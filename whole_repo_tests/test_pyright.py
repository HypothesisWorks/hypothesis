# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest

from hypothesistooling.projects.hypothesispython import HYPOTHESIS_PYTHON, PYTHON_SRC
from hypothesistooling.scripts import pip_tool, tool_path

from .revealed_types import NUMPY_REVEALED_TYPES, PYTHON_VERSIONS, REVEALED_TYPES


@pytest.mark.skip(
    reason="Hypothesis type-annotates the public API as a convenience for users, "
    "but strict checks for our internals would be a net drag on productivity."
)
def test_pyright_passes_on_hypothesis():
    pip_tool("pyright", "--project", HYPOTHESIS_PYTHON)


@pytest.mark.parametrize("python_version", PYTHON_VERSIONS)
def test_pyright_passes_on_basic_test(tmp_path: Path, python_version: str):
    file = tmp_path / "test.py"
    file.write_text(
        textwrap.dedent(
            """
            import hypothesis
            import hypothesis.strategies as st

            @hypothesis.given(x=st.text())
            def test_foo(x: str):
                assert x == x

            from hypothesis import given
            from hypothesis.strategies import text

            @given(x=text())
            def test_bar(x: str):
                assert x == x
            """
        ),
        encoding="utf-8",
    )
    _write_config(
        tmp_path, {"typeCheckingMode": "strict", "pythonVersion": python_version}
    )
    assert _get_pyright_errors(file) == []


@pytest.mark.parametrize(
    "python_version",
    [
        # FIXME: temporary workaround, see hypothesis/pull/4136
        pytest.param(v, marks=[pytest.mark.xfail(strict=False)] * (v == "3.13"))
        for v in PYTHON_VERSIONS
    ],
)
def test_given_only_allows_strategies(tmp_path: Path, python_version: str):
    file = tmp_path / "test.py"
    file.write_text(
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
    _write_config(
        tmp_path, {"typeCheckingMode": "strict", "pythonVersion": python_version}
    )
    errors = _get_pyright_errors(file)
    msg = 'Argument of type "Literal[1]" cannot be assigned to parameter "_given_arguments"'
    assert sum(e["message"].startswith(msg) for e in errors) == 1, errors


def test_pyright_issue_3296(tmp_path: Path):
    file = tmp_path / "test.py"
    file.write_text(
        textwrap.dedent(
            """
            from hypothesis.strategies import lists, integers

            lists(integers()).map(sorted)
            """
        ),
        encoding="utf-8",
    )
    _write_config(tmp_path, {"typeCheckingMode": "strict"})
    assert _get_pyright_errors(file) == []


def test_pyright_raises_for_mixed_pos_kwargs_in_given(tmp_path: Path):
    file = tmp_path / "test.py"
    file.write_text(
        textwrap.dedent(
            """
            from hypothesis import given
            from hypothesis.strategies import text

            @given(text(), x=text())
            def test_bar(x: str):
                pass
            """
        ),
        encoding="utf-8",
    )
    _write_config(tmp_path, {"typeCheckingMode": "strict"})
    assert (
        sum(
            e["message"].startswith(
                'No overloads for "given" match the provided arguments'
            )
            for e in _get_pyright_errors(file)
        )
        == 1
    )


def test_pyright_issue_3348(tmp_path: Path):
    file = tmp_path / "test.py"
    file.write_text(
        textwrap.dedent(
            """
            import hypothesis.strategies as st

            st.tuples(st.integers(), st.integers())
            st.one_of(st.integers(), st.integers())
            st.one_of([st.integers(), st.floats()])  # sequence of strats should be OK
            st.sampled_from([1, 2])
            """
        ),
        encoding="utf-8",
    )
    _write_config(tmp_path, {"typeCheckingMode": "strict"})
    assert _get_pyright_errors(file) == []


def test_numpy_arrays_strategy(tmp_path: Path):
    file = tmp_path / "test.py"
    file.write_text(
        textwrap.dedent(
            """
            import numpy as np
            from hypothesis.extra.numpy import arrays

            x = arrays(dtype=np.dtype("int32"), shape=1)
            """
        ),
        encoding="utf-8",
    )
    _write_config(tmp_path, {"typeCheckingMode": "strict"})
    errors = _get_pyright_errors(file)
    print(errors)
    assert errors == []


@pytest.mark.parametrize(
    "val,expect",
    [
        *REVEALED_TYPES,  # shared with Mypy
        ("lists(none())", "list[None]"),
        ("dictionaries(integers(), datetimes())", "dict[int, datetime]"),
        ("data()", "DataObject"),
        ("none() | integers()", "int | None"),
        ("recursive(integers(), lists)", "list[Any] | int"),
        # We have overloads for up to five types, then fall back to Any.
        # (why five?  JSON atoms are None|bool|int|float|str and we do that a lot)
        ("one_of(integers(), text())", "int | str"),
        (
            "one_of(integers(), text(), none(), binary(), builds(list))",
            "int | str | bytes | list[Unknown] | None",
        ),
        (
            "one_of(integers(), text(), none(), binary(), builds(list), builds(dict))",
            "Any",
        ),
        # Note: keep this in sync with the equivalent test for Mypy
    ],
)
def test_revealed_types(tmp_path, val, expect):
    """Check that Pyright picks up the expected `X` in SearchStrategy[`X`]."""
    f = tmp_path / (expect + ".py")
    f.write_text(
        textwrap.dedent(
            f"""
            from hypothesis.strategies import *
            reveal_type({val})
            """
        ),
        encoding="utf-8",
    )
    _write_config(tmp_path, {"reportWildcardImportFromLibrary ": "none"})
    typ = get_pyright_analysed_type(f)
    assert typ == f"SearchStrategy[{expect}]"


@pytest.mark.parametrize("val,expect", NUMPY_REVEALED_TYPES)
def test_numpy_revealed_types(tmp_path, val, expect):
    f = tmp_path / (expect + ".py")
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
    _write_config(tmp_path, {"reportWildcardImportFromLibrary ": "none"})
    typ = get_pyright_analysed_type(f)
    assert typ == f"SearchStrategy[{expect}]"


@pytest.mark.parametrize(
    "val,expect",
    [
        ("elements=None, fill=None", "Any"),
        ("elements=None, fill=floats()", "float"),
        ("elements=floats(), fill=None", "float"),
        ("elements=floats(), fill=text()", "float | str"),
        # Note: keep this in sync with the equivalent test for Mypy
    ],
)
def test_pandas_column(tmp_path, val, expect):
    f = tmp_path / "test.py"
    f.write_text(
        textwrap.dedent(
            f"""
            from hypothesis.extra.pandas import column
            from hypothesis.strategies import *

            x = column(name="test", unique=True, dtype=None, {val})
            reveal_type(x)
            """
        ),
        encoding="utf-8",
    )
    _write_config(
        tmp_path,
        {"typeCheckingMode": "strict", "reportWildcardImportFromLibrary ": "none"},
    )
    typ = get_pyright_analysed_type(f)
    assert typ == f"column[{expect}]"


def test_pyright_tuples_pos_args_only(tmp_path: Path):
    file = tmp_path / "test.py"
    file.write_text(
        textwrap.dedent(
            """
            import hypothesis.strategies as st

            st.tuples(a1=st.integers())
            st.tuples(a1=st.integers(), a2=st.integers())
            """
        ),
        encoding="utf-8",
    )
    _write_config(tmp_path, {"typeCheckingMode": "strict"})
    assert (
        sum(
            e["message"].startswith(
                'No overloads for "tuples" match the provided arguments'
            )
            for e in _get_pyright_errors(file)
        )
        == 2
    )


def test_pyright_one_of_pos_args_only(tmp_path: Path):
    file = tmp_path / "test.py"
    file.write_text(
        textwrap.dedent(
            """
            import hypothesis.strategies as st

            st.one_of(a1=st.integers())
            st.one_of(a1=st.integers(), a2=st.integers())
            """
        ),
        encoding="utf-8",
    )
    _write_config(tmp_path, {"typeCheckingMode": "strict"})
    assert (
        sum(
            e["message"].startswith(
                'No overloads for "one_of" match the provided arguments'
            )
            for e in _get_pyright_errors(file)
        )
        == 2
    )


def test_register_random_protocol(tmp_path: Path):
    file = tmp_path / "test.py"
    file.write_text(
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
            register_random(None)  # type: ignore
            """
        ),
        encoding="utf-8",
    )
    _write_config(tmp_path, {"reportUnnecessaryTypeIgnoreComment": True})
    assert _get_pyright_errors(file) == []


# ---------- Helpers for running pyright ---------- #


def _get_pyright_output(file: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [tool_path("pyright"), "--outputjson", f"--pythonpath={sys.executable}"],
        cwd=file.parent,
        encoding="utf-8",
        text=True,
        capture_output=True,
    )
    try:
        return json.loads(proc.stdout)
    except Exception:
        print(proc.stdout)
        raise


def _get_pyright_errors(file: Path) -> list[dict[str, Any]]:
    return _get_pyright_output(file)["generalDiagnostics"]


def get_pyright_analysed_type(fname):
    out, *rest = _get_pyright_errors(fname)
    print(out, rest)
    assert not rest
    assert out["severity"] == "information"
    return (
        re.fullmatch(r'Type of ".+" is "(.+)"', out["message"])
        .group(1)
        .replace("builtins.", "")
        .replace("numpy.", "")
        .replace(
            "signedinteger[_32Bit | _64Bit] | bool[bool]",
            "Union[signedinteger[Union[_32Bit, _64Bit]], bool[bool]]",
        )
    )


def _write_config(config_dir: Path, data: dict[str, Any] | None = None):
    config = {"extraPaths": [str(PYTHON_SRC)], **(data or {})}
    (config_dir / "pyrightconfig.json").write_text(json.dumps(config), encoding="utf-8")
