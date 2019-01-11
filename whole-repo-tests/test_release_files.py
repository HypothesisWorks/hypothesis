# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
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

from __future__ import absolute_import, division, print_function

import pytest

import hypothesistooling as tools
import hypothesistooling.releasemanagement as rm


@pytest.mark.parametrize("project", tools.all_projects())
def test_release_file_exists_and_is_valid(project):
    if project.has_source_changes():
        assert project.has_release(), (
            "There are source changes but no RELEASE.rst. Please create "
            "one to describe your changes."
        )
        rm.parse_release_file(project.RELEASE_FILE)
