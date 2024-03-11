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

from hypothesistooling.releasemanagement import (
    bump_version_info,
    parse_release_file_contents,
    release_date_string,
    replace_assignment_in_string as replace,
    update_markdown_changelog,
)


def parse_release(contents):
    return parse_release_file_contents(contents, "<string>")


def test_update_single_line():
    assert replace("a = 1", "a", "2") == "a = 2"


def test_update_without_spaces():
    assert replace("a=1", "a", "2") == "a=2"


def test_update_in_middle():
    assert replace("a = 1\nb=2\nc = 3", "b", "4") == "a = 1\nb=4\nc = 3"


def test_quotes_string_to_assign():
    assert replace("a.c = 1", "a.c", "2") == "a.c = 2"
    with pytest.raises(ValueError):
        replace("abc = 1", "a.c", "2")


def test_duplicates_are_errors():
    with pytest.raises(ValueError):
        replace("a = 1\na=1", "a", "2")


def test_missing_is_error():
    with pytest.raises(ValueError):
        replace("", "a", "1")


def test_bump_minor_version():
    assert bump_version_info((1, 1, 1), "minor")[0] == "1.2.0"


def test_parse_release_file():
    assert parse_release("RELEASE_TYPE: patch\nhi") == ("patch", "hi")
    assert parse_release("RELEASE_TYPE: minor\n\n\n\nhi") == ("minor", "hi")
    assert parse_release("RELEASE_TYPE: major\n \n\nhi") == ("major", "hi")


def test_invalid_release():
    with pytest.raises(ValueError):
        parse_release("RELEASE_TYPE: wrong\nstuff")

    with pytest.raises(ValueError):
        parse_release("")


TEST_CHANGELOG = f"""
# A test project 1.2.3 ({release_date_string()})

some stuff happened

# some previous log entry
"""


def test_update_changelog(tmp_path):
    path = tmp_path / "CHANGELOG.md"
    path.write_text("# some previous log entry\n", encoding="utf-8")
    update_markdown_changelog(
        str(path), "A test project", "1.2.3", "some stuff happened"
    )
    assert path.read_text(encoding="utf-8").strip() == TEST_CHANGELOG.strip()


def test_changelog_parsing_strips_trailing_whitespace():
    header = "RELEASE_TYPE: patch\n\n"
    contents = "Adds a feature\n    indented.\n"
    level, out = parse_release(header + contents.replace("feature", "feature    "))
    assert contents.strip() == out
