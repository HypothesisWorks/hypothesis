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

from hypothesistooling import release


def test_release_file_exists_and_is_valid():
    if release.has_source_changes():
        assert release.has_release(), (
            "There are source changes but no RELEASE.rst. Please create "
            "one to describe your changes. An example can be found in "
            "RELEASE-sample.rst."
        )
        assert release.has_release_sample(), (
            "The RELEASE-sample.rst file is missing. Please copy it "
            "to RELEASE.rst, rather than moving it."
        )
        release.parse_release_file()


@pytest.mark.skipif(not release.has_release(), reason="Checking that release")
def test_release_file_has_no_merge_conflicts():
    _, message = release.parse_release_file()
    assert "<<<" not in message, "Merge conflict in RELEASE.rst"
    if message in {release.get_autoupdate_message(x).strip() for x in (True, False)}:
        return
    _, *recent_changes, _ = release.CHANGELOG_ANCHOR.split(
        release.changelog(), maxsplit=12
    )
    for entry in recent_changes:
        _, version, old_msg = (x.strip() for x in release.CHANGELOG_BORDER.split(entry))
        assert message not in old_msg, f"Release notes already published for {version}"
        assert old_msg not in message, f"Copied {version} release notes - merge error?"
