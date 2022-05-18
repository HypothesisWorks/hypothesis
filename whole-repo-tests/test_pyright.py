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
import subprocess
import textwrap
from pathlib import Path
from typing import Any

import pytest

from hypothesistooling.projects.hypothesispython import HYPOTHESIS_PYTHON, PYTHON_SRC
from hypothesistooling.scripts import pip_tool, tool_path


@pytest.mark.skip(
    reason="Hypothesis type-annotates the public API as a convenience for users, "
    "but strict checks for our internals would be a net drag on productivity."
)
def test_pyright_passes_on_hypothesis():
    pip_tool("pyright", "--project", HYPOTHESIS_PYTHON)


def test_pyright_passes_on_basic_test(tmp_path: Path):
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
        )
    )
    _write_config(tmp_path, {"typeCheckingMode": "strict"})
    assert _get_pyright_errors(file) == []


def test_pyright_issue_3296(tmp_path: Path):
    file = tmp_path / "test.py"
    file.write_text(
        textwrap.dedent(
            """
            from hypothesis.strategies import lists, integers

            lists(integers()).map(sorted)
            """
        )
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
        )
    )
    _write_config(tmp_path, {"typeCheckingMode": "strict"})
    assert any(
        e["message"].startswith('No overloads for "given" match the provided arguments')
        for e in _get_pyright_errors(file)
    )


def test_pyright_issue_3348(tmp_path: Path):
    file = tmp_path / "test.py"
    file.write_text(
        textwrap.dedent(
            """
            import hypothesis.strategies as st

            st.tuples(st.integers())
            st.tuples(st.integers(), st.integers())
            """
        )
    )
    _write_config(tmp_path, {"typeCheckingMode": "strict"})
    assert _get_pyright_errors(file) == []


def test_pyright_tuples_pos_args_only(tmp_path: Path):
    file = tmp_path / "test.py"
    file.write_text(
        textwrap.dedent(
            """
            import hypothesis.strategies as st

            st.tuples(a1=st.integers())
            st.tuples(a1=st.integers(), a2=st.integers())
            """
        )
    )
    _write_config(tmp_path, {"typeCheckingMode": "strict"})
    assert any(
        e["message"].startswith(
            'No overloads for "tuples" match the provided arguments'
        )
        for e in _get_pyright_errors(file)
    )


# ---------- Helpers for running pyright ---------- #


def _get_pyright_output(file: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [tool_path("pyright"), "--outputjson"],
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


def _write_config(config_dir: Path, data: dict[str, Any] | None = None):
    config = {"extraPaths": [PYTHON_SRC], **(data or {})}
    (config_dir / "pyrightconfig.json").write_text(json.dumps(config))
