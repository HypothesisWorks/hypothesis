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

"""Helpful common code for release management tasks that is shared across
multiple projects.

Note that most code in here is brittle and specific to our build and
probably makes all sorts of undocumented assumptions, even as it looks
like a nice tidy reusable set of functionality.
"""


from __future__ import absolute_import, division, print_function

import re
from datetime import datetime

import hypothesistooling as tools

__RELEASE_DATE_STRING = None


def release_date_string():
    """Returns a date string that represents what should be considered "today"
    for the purposes of releasing, and ensure that we don't change part way
    through a release."""
    global __RELEASE_DATE_STRING
    if __RELEASE_DATE_STRING is None:
        __RELEASE_DATE_STRING = datetime.utcnow().strftime("%Y-%m-%d")
    return __RELEASE_DATE_STRING


def assignment_matcher(name):
    """
    Matches a single line of the form (some space)name = (some value). e.g.
    "  foo = 1".
    The whole line up to the assigned value is the first matching group,
    the rest of the line is the second matching group.
    i.e. group 1 is the assignment, group 2 is the value. In the above
    example group 1 would be "  foo = " and group 2 would be "1"
    """
    return re.compile(r"\A(\s*%s\s*=\s*)(.+)\Z" % (re.escape(name),))


def extract_assignment_from_string(contents, name):
    lines = contents.split("\n")

    matcher = assignment_matcher(name)

    for l in lines:
        match = matcher.match(l)
        if match is not None:
            return match[2].strip()

    raise ValueError("Key %s not found in %s" % (name, contents))


def extract_assignment(filename, name):
    with open(filename) as i:
        return extract_assignment_from_string(i.read(), name)


def replace_assignment_in_string(contents, name, value):
    lines = contents.split("\n")

    matcher = assignment_matcher(name)

    count = 0

    for i, l in enumerate(lines):
        match = matcher.match(l)
        if match is not None:
            count += 1
            lines[i] = match[1] + value

    if count == 0:
        raise ValueError("Key %s not found in %s" % (name, contents))
    if count > 1:
        raise ValueError("Key %s found %d times in %s" % (name, count, contents))

    return "\n".join(lines)


def replace_assignment(filename, name, value):
    """Replaces a single assignment of the form key = value in a file with a
    new value, attempting to preserve the existing format.

    This is fairly fragile - in particular it knows nothing about
    the file format. The existing value is simply the rest of the line after
    the last space after the equals.
    """
    with open(filename) as i:
        contents = i.read()
    result = replace_assignment_in_string(contents, name, value)
    with open(filename, "w") as o:
        o.write(result)


RELEASE_TYPE = re.compile(r"^RELEASE_TYPE: +(major|minor|patch)")


MAJOR = "major"
MINOR = "minor"
PATCH = "patch"


VALID_RELEASE_TYPES = (MAJOR, MINOR, PATCH)


def parse_release_file(filename):
    with open(filename) as i:
        return parse_release_file_contents(i.read(), filename)


def parse_release_file_contents(release_contents, filename):
    release_lines = [l.rstrip() for l in release_contents.split("\n")]

    m = RELEASE_TYPE.match(release_lines[0])
    if m is not None:
        release_type = m.group(1)
        if release_type not in VALID_RELEASE_TYPES:
            raise ValueError("Unrecognised release type %r" % (release_type,))
        del release_lines[0]
        release_contents = "\n".join(release_lines).strip()
    else:
        raise ValueError(
            "%s does not start by specifying release type. The first "
            "line of the file should be RELEASE_TYPE: followed by one of "
            "major, minor, or patch, to specify the type of release that "
            "this is (i.e. which version number to increment). Instead the "
            "first line was %r" % (filename, release_lines[0])
        )

    return release_type, release_contents


def bump_version_info(version_info, release_type):
    new_version = list(version_info)
    bump = VALID_RELEASE_TYPES.index(release_type)
    new_version[bump] += 1
    for i in range(bump + 1, len(new_version)):
        new_version[i] = 0
    new_version = tuple(new_version)
    new_version_string = ".".join(map(str, new_version))
    return new_version_string, new_version


def update_markdown_changelog(changelog, name, version, entry):
    with open(changelog) as i:
        prev_contents = i.read()

    title = "# %(name)s %(version)s (%(date)s)\n\n" % {
        "name": name,
        "version": version,
        "date": release_date_string(),
    }

    with open(changelog, "w") as o:
        o.write(title)
        o.write(entry.strip())
        o.write("\n\n")
        o.write(prev_contents)


def parse_version(version):
    return tuple(map(int, version.split(".")))


def commit_pending_release(project):
    """Create a commit with the new release."""
    tools.git("rm", project.RELEASE_FILE)
    tools.git("add", "-u", project.BASE_DIR)

    tools.git(
        "commit",
        "-m",
        "Bump %s version to %s and update changelog"
        "\n\n[skip ci]" % (project.PACKAGE_NAME, project.current_version()),
    )
