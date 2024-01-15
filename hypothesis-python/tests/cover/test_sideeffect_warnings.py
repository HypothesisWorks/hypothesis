# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from pathlib import Path
import warnings

import pytest

import _hypothesis_globals
from hypothesis import configuration as fs
from hypothesis.errors import HypothesisSideeffectWarning
from hypothesis import strategies as st

IN_INITIALIZATION_ATTR = "in_initialization"


@pytest.fixture
def extend_initialization(monkeypatch):
    monkeypatch.setattr(_hypothesis_globals, IN_INITIALIZATION_ATTR, 1)
    fs.notice_initialization_restarted(warn=False)


@pytest.mark.parametrize(
    "sideeffect_script, warning_text",
    [
        ("st.integers().is_empty", "lazy evaluation"),
        ("st.deferred(st.integers).is_empty", "deferred evaluation"),
        ("fs.storage_directory()", "accessing storage"),
    ],
)
def test_sideeffect_warning(sideeffect_script, warning_text, extend_initialization):
    with pytest.warns(HypothesisSideeffectWarning, match=warning_text):
        exec(sideeffect_script)


def test_sideeffect_delayed_warning(monkeypatch, extend_initialization):
    what = "synthetic side-effect"
    # extend_initialization ensures we start at known clean slate (no delayed warnings).
    # Then: stop initialization, check a side-effect operation, and restart it.
    monkeypatch.setattr(_hypothesis_globals, IN_INITIALIZATION_ATTR, 0)
    fs.check_sideeffect_during_initialization(what)
    fs.check_sideeffect_during_initialization("ignored since not first")
    with pytest.warns(HypothesisSideeffectWarning, match=what):
        monkeypatch.setattr(_hypothesis_globals, IN_INITIALIZATION_ATTR, 1)
        fs.notice_initialization_restarted()
