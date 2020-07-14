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
import subprocess

import hypothesistooling as tools
from hypothesistooling import installers as install, releasemanagement as rm
from hypothesistooling.junkdrawer import in_dir, unlink_if_present, unquote_string

PACKAGE_NAME = "conjecture-rust"

CONJECTURE_RUST = os.path.join(tools.ROOT, PACKAGE_NAME)

BASE_DIR = CONJECTURE_RUST

TAG_PREFIX = PACKAGE_NAME + "-"

RELEASE_FILE = os.path.join(BASE_DIR, "RELEASE.md")
CHANGELOG_FILE = os.path.join(BASE_DIR, "CHANGELOG.md")

CARGO_FILE = os.path.join(BASE_DIR, "Cargo.toml")

SRC = os.path.join(BASE_DIR, "lib")


def has_release():
    """Is there a version of this package ready to release?"""
    return os.path.exists(RELEASE_FILE)


def update_changelog_and_version():
    """Update the changelog and version based on the current release file."""
    release_type, release_contents = rm.parse_release_file(RELEASE_FILE)
    version = current_version()
    version_info = rm.parse_version(version)

    version, version_info = rm.bump_version_info(version_info, release_type)

    rm.replace_assignment(CARGO_FILE, "version", repr(version))

    rm.update_markdown_changelog(
        CHANGELOG_FILE,
        name="Conjecture for Rust",
        version=version,
        entry=release_contents,
    )
    os.unlink(RELEASE_FILE)


def cargo(*args):
    install.ensure_rustup()
    with in_dir(BASE_DIR):
        subprocess.check_call(("cargo",) + args)


IN_TEST = False


def build_distribution():
    """Build the crate."""
    if IN_TEST:
        cargo("package", "--allow-dirty")
    else:
        cargo("package")


def tag_name():
    """The tag name for the upcoming release."""
    return TAG_PREFIX + current_version()


def has_source_changes():
    """Returns True if any source files have changed."""
    return tools.has_changes([SRC])


def current_version():
    """Returns the current version as specified by the Cargo.toml."""
    return unquote_string(rm.extract_assignment(CARGO_FILE, "version"))


CARGO_CREDENTIALS = os.path.expanduser("~/.cargo/credentials")


def upload_distribution():
    """Upload the built package to crates.io."""
    tools.assert_can_release()

    # Yes, cargo really will only look in this file. Yes this is terrible.
    # This only runs on Travis, so we may be assumed to own it, but still.
    unlink_if_present(CARGO_CREDENTIALS)

    # symlink so that the actual secret credentials can't be leaked via the
    # cache.
    os.symlink(tools.CARGO_API_KEY, CARGO_CREDENTIALS)

    # Give the key the right permissions.
    os.chmod(CARGO_CREDENTIALS, int("0600", 8))

    cargo("publish")
