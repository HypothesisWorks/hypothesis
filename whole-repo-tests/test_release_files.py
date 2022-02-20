# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

import hypothesistooling as tools
from hypothesistooling import releasemanagement as rm


@pytest.mark.parametrize("project", tools.all_projects())
def test_release_file_exists_and_is_valid(project):
    if project.has_source_changes():
        assert project.has_release(), (
            "There are source changes but no RELEASE.rst. Please create "
            "one to describe your changes."
        )
        rm.parse_release_file(project.RELEASE_FILE)
