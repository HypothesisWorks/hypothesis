# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import textwrap

import pytest

from hypothesistooling.projects.hypothesispython import PYTHON_SRC
from hypothesistooling.scripts import pip_tool

from .revealed_types import PYTHON_VERSIONS
from .test_mypy import assert_mypy_errors


def test_mypy_passes_on_hypothesis():
    pip_tool("mypy", str(PYTHON_SRC))


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
