# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import _hypothesis_globals
import pytest

from hypothesis import configuration as fs, strategies as st
from hypothesis.errors import HypothesisSideeffectWarning

IN_INITIALIZATION_ATTR = "in_initialization"

# These tests use the pytest plugin enabling infrastructure to restart the side-effect warnings,
# rather than trying to induce side-effects during import (and entrypoint loading) itself, which is
# hard to do.  Manual verification of behaviour during initial import can be done by just injecting
# one of the side-effect-inducing statements below directly into hypothesis.entry_points.run().
# Manual validation can also be done by inspecting the relevant state during import and verify that
# it is the same as tested here
# (_hypothesis_globals.in_initialization > 0, hypothesis.configuration._first_postinit_what is None)


@pytest.fixture
def _extend_initialization(monkeypatch):
    assert getattr(_hypothesis_globals, IN_INITIALIZATION_ATTR) <= 0
    monkeypatch.setattr(_hypothesis_globals, IN_INITIALIZATION_ATTR, 1)
    fs.notice_initialization_restarted(warn=False)
    assert fs._first_postinit_what is None  # validates state as given in comment above


@pytest.mark.parametrize(
    "sideeffect, warning_text",
    [
        # the inner lambda ensures the lazy strategy can't be cached
        (lambda: st.builds(lambda: None).wrapped_strategy, "lazy evaluation"),
        (lambda: st.deferred(st.none).wrapped_strategy, "deferred evaluation"),
        (fs.storage_directory, "accessing storage"),
    ],
)
def test_sideeffect_warning(sideeffect, warning_text, _extend_initialization):
    with pytest.warns(HypothesisSideeffectWarning, match=warning_text):
        sideeffect()


def test_sideeffect_delayed_warning(monkeypatch, _extend_initialization):
    what = "synthetic side-effect"
    # _extend_initialization ensures we start at known clean slate (no delayed warnings).
    # Then: stop initialization, check a side-effect operation, and restart it.
    monkeypatch.setattr(_hypothesis_globals, IN_INITIALIZATION_ATTR, 0)
    fs.check_sideeffect_during_initialization(what)
    fs.check_sideeffect_during_initialization("ignored since not first")
    # The warning should identify itself as happening after import but before plugin load
    with pytest.warns(HypothesisSideeffectWarning, match=what + ".*between import"):
        monkeypatch.setattr(_hypothesis_globals, IN_INITIALIZATION_ATTR, 1)
        fs.notice_initialization_restarted()
