# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

import os

import pytest

import hypothesistooling as tools
from hypothesistooling import __main__ as main, releasemanagement as rm


@pytest.mark.parametrize(
    "project", [p for p in tools.all_projects() if p.has_release()]
)
def test_release_file_exists_and_is_valid(project, monkeypatch):
    assert not tools.has_uncommitted_changes(project.BASE_DIR)

    monkeypatch.setattr(tools, "create_tag", lambda *args, **kwargs: None)
    monkeypatch.setattr(tools, "push_tag", lambda name: None)
    monkeypatch.setattr(rm, "commit_pending_release", lambda p: None)
    monkeypatch.setattr(project, "upload_distribution", lambda: None)
    monkeypatch.setattr(project, "IN_TEST", True, raising=False)

    try:
        main.do_release(project)

        with open(project.CHANGELOG_FILE) as i:
            changelog = i.read()
        assert project.current_version() in changelog
        assert rm.release_date_string() in changelog

    finally:
        tools.git("checkout", project.BASE_DIR)
        os.chdir(tools.ROOT)
