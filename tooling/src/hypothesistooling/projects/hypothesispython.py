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

import os
import re
import shutil
import subprocess
import sys

import requests

import hypothesistooling as tools
import hypothesistooling.releasemanagement as rm

PACKAGE_NAME = "hypothesis-python"

HYPOTHESIS_PYTHON = os.path.join(tools.ROOT, PACKAGE_NAME)
PYTHON_TAG_PREFIX = "hypothesis-python-"


BASE_DIR = HYPOTHESIS_PYTHON

PYTHON_SRC = os.path.join(HYPOTHESIS_PYTHON, "src")
PYTHON_TESTS = os.path.join(HYPOTHESIS_PYTHON, "tests")

RELEASE_FILE = os.path.join(HYPOTHESIS_PYTHON, "RELEASE.rst")

assert os.path.exists(PYTHON_SRC)


__version__ = None
__version_info__ = None

VERSION_FILE = os.path.join(PYTHON_SRC, "hypothesis/version.py")

with open(VERSION_FILE) as o:
    exec(o.read())

assert __version__ is not None
assert __version_info__ is not None


def has_release():
    return os.path.exists(RELEASE_FILE)


def parse_release_file():
    return rm.parse_release_file(RELEASE_FILE)


def has_source_changes():
    return tools.has_changes([PYTHON_SRC])


CHANGELOG_ANCHOR = re.compile(r"^\.\. _v\d+\.\d+\.\d+:$")
CHANGELOG_BORDER = re.compile(r"^-+$")
CHANGELOG_HEADER = re.compile(r"^\d+\.\d+\.\d+ - \d\d\d\d-\d\d-\d\d$")


def update_changelog_and_version():
    global __version_info__
    global __version__

    contents = changelog()
    assert "\r" not in contents
    lines = contents.split("\n")
    for i, l in enumerate(lines):
        if CHANGELOG_ANCHOR.match(l):
            assert CHANGELOG_BORDER.match(lines[i + 2]), repr(lines[i + 2])
            assert CHANGELOG_HEADER.match(lines[i + 3]), repr(lines[i + 3])
            assert CHANGELOG_BORDER.match(lines[i + 4]), repr(lines[i + 4])
            beginning = "\n".join(lines[:i])
            rest = "\n".join(lines[i:])
            assert "\n".join((beginning, rest)) == contents
            break

    release_type, release_contents = parse_release_file()

    new_version_string, new_version_info = rm.bump_version_info(
        __version_info__, release_type
    )

    __version_info__ = new_version_info
    __version__ = new_version_string

    rm.replace_assignment(VERSION_FILE, "__version_info__", repr(new_version_info))

    heading_for_new_version = " - ".join((new_version_string, rm.release_date_string()))
    border_for_new_version = "-" * len(heading_for_new_version)

    new_changelog_parts = [
        beginning.strip(),
        "",
        ".. _v%s:" % (new_version_string),
        "",
        border_for_new_version,
        heading_for_new_version,
        border_for_new_version,
        "",
        release_contents,
        "",
        rest,
    ]

    with open(CHANGELOG_FILE, "w") as o:
        o.write("\n".join(new_changelog_parts))

    # Replace the `since="RELEASEDAY"` argument to `note_deprecation`
    # with today's date, to record it for future reference.
    before = 'since="RELEASEDAY"'
    after = before.replace("RELEASEDAY", rm.release_date_string())
    for root, _, files in os.walk(PYTHON_SRC):
        for fname in (os.path.join(root, f) for f in files if f.endswith(".py")):
            with open(fname) as f:
                contents = f.read()
            if before in contents:
                with open(fname, "w") as f:
                    f.write(contents.replace(before, after))


CHANGELOG_FILE = os.path.join(HYPOTHESIS_PYTHON, "docs", "changes.rst")
DIST = os.path.join(HYPOTHESIS_PYTHON, "dist")


def changelog():
    with open(CHANGELOG_FILE) as i:
        return i.read()


def build_distribution():
    if os.path.exists(DIST):
        shutil.rmtree(DIST)

    subprocess.check_output([sys.executable, "setup.py", "sdist", "--dist-dir", DIST])


def upload_distribution():
    tools.assert_can_release()
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "twine",
            "upload",
            "--config-file",
            tools.PYPIRC,
            os.path.join(DIST, "*"),
        ]
    )
    # Create a GitHub release, to trigger Zenodo DOI minting.  See
    # https://developer.github.com/v3/repos/releases/#create-a-release
    requests.post(
        "https://api.github.com/repos/HypothesisWorks/hypothesis/releases",
        json=dict(
            tag_name=tag_name(),
            name="Hypothesis for Python - version " + current_version(),
            body=(
                "You can [read the changelog for this release here]("
                "https://hypothesis.readthedocs.io/en/latest/changes.html#v"
                "%s)." % (current_version().replace(".", "-"),)
            ),
        ),
        timeout=120,  # seconds
        # Scoped personal access token, stored in Travis environ variable
        auth=("Zac-HD", os.environ["Zac_release_token"]),
    ).raise_for_status()


def current_version():
    return __version__


def latest_version():
    versions = []

    for t in tools.tags():
        if t.startswith(PYTHON_TAG_PREFIX):
            t = t[len(PYTHON_TAG_PREFIX) :]
        else:
            continue
        assert t == t.strip()
        parts = t.split(".")
        assert len(parts) == 3
        v = tuple(map(int, parts))
        versions.append((v, t))

    _, latest = max(versions)

    return latest


def tag_name():
    return PYTHON_TAG_PREFIX + __version__
