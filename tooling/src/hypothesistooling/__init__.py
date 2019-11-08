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
import shlex
import subprocess


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


ROOT = (
    subprocess.check_output(
        ["git", "-C", os.path.dirname(__file__), "rev-parse", "--show-toplevel"]
    )
    .decode("ascii")
    .strip()
)


REPO_TESTS = os.path.join(ROOT, "whole-repo-tests")

PYUP_FILE = os.path.join(ROOT, ".pyup.yml")


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
    subprocess.check_call(("git",) + args)


TOOLING_COMMITER_NAME = "Travis CI on behalf of David R. MacIver"


def configure_git():
    git("config", "user.name", TOOLING_COMMITER_NAME)
    git("config", "user.email", "david@drmaciver.com")
    git("config", "core.sshCommand", "ssh -i deploy_key")
    git("remote", "add", "ssh-origin", "git@github.com:HypothesisWorks/hypothesis.git")


def create_tag(tagname):
    assert tagname not in tags()
    git("tag", tagname)


def push_tag(tagname):
    assert_can_release()
    subprocess.check_call(
        [
            "ssh-agent",
            "sh",
            "-c",
            "ssh-add %s && " % (shlex.quote(DEPLOY_KEY),)
            + "git push ssh-origin HEAD:master &&"
            + "git push ssh-origin %s" % (shlex.quote(tagname),),
        ]
    )


def assert_can_release():
    assert not IS_PULL_REQUEST, "Cannot release from pull requests"
    assert has_travis_secrets(), "Cannot release without travis secure vars"


def has_travis_secrets():
    return os.environ.get("TRAVIS_SECURE_ENV_VARS", None) == "true"


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
            if filepath:
                assert os.path.exists(filepath), filepath
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
    """Returns a list of files which have changed between a branch and
    master."""
    files = set()
    command = ["git", "diff", "--name-only", "HEAD", "master"]
    diff_output = subprocess.check_output(command).decode("ascii")
    for line in diff_output.splitlines():
        filepath = line.strip()
        if filepath:
            files.add(filepath)
    return files


SECRETS_BASE = os.path.join(ROOT, "secrets")
SECRETS_TAR = SECRETS_BASE + ".tar"
ENCRYPTED_SECRETS = SECRETS_TAR + ".enc"

SECRETS = os.path.join(ROOT, "secrets")

DEPLOY_KEY = os.path.join(SECRETS, "deploy_key")
PYPIRC = os.path.join(SECRETS, ".pypirc")

CARGO_API_KEY = os.path.join(SECRETS, "cargo-credentials")


SECRET_FILES = [DEPLOY_KEY, PYPIRC, CARGO_API_KEY]


def decrypt_secrets():
    subprocess.check_call(
        [
            "openssl",
            "aes-256-cbc",
            "-K",
            os.environ["encrypted_b8618e5d043b_key"],
            "-iv",
            os.environ["encrypted_b8618e5d043b_iv"],
            "-in",
            ENCRYPTED_SECRETS,
            "-out",
            SECRETS_TAR,
            "-d",
        ]
    )

    subprocess.check_call(["tar", "-xvf", SECRETS_TAR], cwd=ROOT)

    missing_files = [os.path.basename(f) for f in SECRET_FILES if not os.path.exists(f)]

    assert not missing_files, missing_files
    os.chmod(DEPLOY_KEY, int("0600", 8))


IS_TRAVIS_PULL_REQUEST = os.environ.get("TRAVIS_EVENT_TYPE") == "pull_request"

IS_CIRCLE_PULL_REQUEST = (
    os.environ.get("CIRCLE_BRANCH") == "master"
    and os.environ.get("CI_PULL_REQUESTS", "") != ""
)


IS_PULL_REQUEST = IS_TRAVIS_PULL_REQUEST or IS_CIRCLE_PULL_REQUEST


def all_projects():
    import hypothesistooling.projects.conjecturerust as cr
    import hypothesistooling.projects.hypothesispython as hp

    return [cr, hp]
