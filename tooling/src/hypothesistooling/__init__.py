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
import shlex
import subprocess
from pathlib import Path


def current_branch():
    return (
        subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        .decode("ascii")
        .strip()
    )


def tags():
    result = [
        t.decode("ascii") for t in subprocess.check_output(["git", "tag"]).split(b"\n")
    ]
    assert len(set(result)) == len(result)
    return set(result)


ROOT = Path(
    subprocess.check_output(
        ["git", "-C", os.path.dirname(__file__), "rev-parse", "--show-toplevel"]
    )
    .decode("ascii")
    .strip()
)
REPO_TESTS = ROOT / "whole_repo_tests"


def hash_for_name(name):
    return subprocess.check_output(["git", "rev-parse", name]).decode("ascii").strip()


def is_ancestor(a, b):
    check = subprocess.call(["git", "merge-base", "--is-ancestor", a, b])
    assert 0 <= check <= 1
    return check == 0


def merge_base(a, b):
    return subprocess.check_output(["git", "merge-base", a, b]).strip()


def point_of_divergence():
    return merge_base("HEAD", "origin/master")


def has_changes(files):
    command = [
        "git",
        "diff",
        "--no-patch",
        "--exit-code",
        point_of_divergence(),
        "HEAD",
        "--",
        *files,
    ]
    return subprocess.call(command) != 0


def has_uncommitted_changes(filename):
    return subprocess.call(["git", "diff", "--exit-code", filename]) != 0


def last_committer():
    out, _ = subprocess.Popen(
        ["git", "log", "-1", "--pretty=format:%an"],
        stdout=subprocess.PIPE,
        universal_newlines=True,
    ).communicate()
    return out


def git(*args):
    subprocess.check_call(("git", *args))


TOOLING_COMMITER_NAME = "CI on behalf of the Hypothesis team"


def configure_git():
    git("config", "user.name", TOOLING_COMMITER_NAME)
    git("config", "user.email", "david@drmaciver.com")


def create_tag(tagname):
    assert tagname not in tags()
    git("tag", tagname)


def push_tag(tagname):
    assert_can_release()
    subprocess.check_call(["git", "push", "origin", shlex.quote(tagname)])
    subprocess.check_call(["git", "push", "origin", "HEAD:master"])


def assert_can_release():
    assert not IS_PULL_REQUEST, "Cannot release from pull requests"


def modified_files():
    files = set()
    for command in [
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=d",
            point_of_divergence(),
            "HEAD",
        ],
        ["git", "diff", "--name-only"],
    ]:
        diff_output = subprocess.check_output(command).decode("ascii")
        for l in diff_output.split("\n"):
            filepath = l.strip()
            if filepath and os.path.exists(filepath):
                files.add(filepath)
    return files


def all_files():
    return [
        f
        for f in subprocess.check_output(["git", "ls-files"])
        .decode("ascii")
        .splitlines()
        if os.path.exists(f)
    ]


def changed_files_from_master():
    """Returns a list of files which have changed between a branch and master."""
    files = set()
    command = ["git", "diff", "--name-only", "HEAD", "master"]
    diff_output = subprocess.check_output(command).decode("ascii")
    for line in diff_output.splitlines():
        filepath = line.strip()
        if filepath:
            files.add(filepath)
    return files


IS_PULL_REQUEST = os.environ.get("GITHUB_REF", "").startswith("refs/pull/")


def all_projects():
    import hypothesistooling.projects.conjecturerust as cr
    import hypothesistooling.projects.hypothesispython as hp
    import hypothesistooling.projects.hypothesisruby as hr

    return [cr, hp, hr]
