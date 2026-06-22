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

import pytest

from hypothesistooling import __main__ as main, release
from hypothesistooling.git import ROOT, git, has_uncommitted_changes
from hypothesistooling.release import (
    CHANGELOG_FILE,
    HYPOTHESIS,
    current_version,
    has_release,
    release_date_string,
)


@pytest.mark.skipif(not has_release(), reason="no release file")
def test_do_publish_updates_changelog(monkeypatch):
    if has_uncommitted_changes(HYPOTHESIS):
        pytest.xfail("Cannot run release process with uncommitted changes")

    uploaded = {}
    monkeypatch.setattr(
        main,
        "upload_distribution_to_pypi",
        lambda *, expected_version: uploaded.update(version=expected_version),
    )
    monkeypatch.setattr(main, "create_github_release", lambda: None)
    monkeypatch.setattr(main, "commit_pending_release", lambda: None)
    monkeypatch.setattr(main, "create_tag", lambda name: None)
    monkeypatch.setattr(main, "push_tag", lambda name: None)

    old_version = release.__version__, release.__version_info__
    try:
        main.do_publish()

        changelog = CHANGELOG_FILE.read_text(encoding="utf-8")
        assert current_version() in changelog
        assert release_date_string() in changelog
        assert uploaded["version"] == current_version()
    finally:
        release.__version__, release.__version_info__ = old_version
        git("checkout", str(HYPOTHESIS))
        os.chdir(ROOT)
