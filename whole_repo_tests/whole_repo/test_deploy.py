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

import hypothesistooling as tools
from hypothesistooling import __main__ as main, releasemanagement as rm


@pytest.mark.parametrize(
    "project", [p for p in tools.all_projects() if p.has_release()]
)
def test_release_file_exists_and_is_valid(project, monkeypatch):
    if not tools.has_uncommitted_changes(project.BASE_DIR):
        pytest.xfail("Cannot run release process with uncommitted changes")

    monkeypatch.setattr(tools, "create_tag", lambda *args, **kwargs: None)
    monkeypatch.setattr(tools, "push_tag", lambda name: None)
    monkeypatch.setattr(rm, "commit_pending_release", lambda p: None)
    monkeypatch.setattr(project, "upload_distribution", lambda: None)
    monkeypatch.setattr(project, "IN_TEST", True, raising=False)

    try:
        main.do_release(project)

        with open(project.CHANGELOG_FILE, encoding="utf-8") as i:
            changelog = i.read()
        assert project.current_version() in changelog
        assert rm.release_date_string() in changelog

    finally:
        tools.git("checkout", project.BASE_DIR)
        os.chdir(tools.ROOT)
