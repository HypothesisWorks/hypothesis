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


# ---------- Helpers for running pyright ---------- #


def _get_pyright_output(file: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [tool_path("pyright"), "--outputjson"],
        cwd=file.parent,
        encoding="utf-8",
        universal_newlines=True,
        capture_output=True,
    )
    return json.loads(proc.stdout)


def _get_pyright_errors(file: Path) -> list[dict[str, Any]]:
    return _get_pyright_output(file)["generalDiagnostics"]


def _write_config(config_dir: Path, data: dict[str, Any] | None = None):
    config = {"extraPaths": [PYTHON_SRC], **(data or {})}
    (config_dir / "pyrightconfig.json").write_text(json.dumps(config))
