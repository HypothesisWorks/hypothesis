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
import subprocess

import hypothesistooling as tools
from hypothesistooling import installers as install, releasemanagement as rm
from hypothesistooling.junkdrawer import in_dir, unquote_string

PACKAGE_NAME = "conjecture-rust"

CONJECTURE_RUST = os.path.join(tools.ROOT, PACKAGE_NAME)

BASE_DIR = CONJECTURE_RUST

TAG_PREFIX = PACKAGE_NAME + "-"

RELEASE_FILE = os.path.join(BASE_DIR, "RELEASE.md")
CHANGELOG_FILE = os.path.join(BASE_DIR, "CHANGELOG.md")

CARGO_FILE = os.path.join(BASE_DIR, "Cargo.toml")

SRC = os.path.join(BASE_DIR, "src")


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


def cargo(*args):
    install.ensure_rustup()
    with in_dir(BASE_DIR):
        subprocess.check_call(("cargo", *args))


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
    # Credentials are supplied by the CARGO_REGISTRY_TOKEN envvar, which in turn
    # is set from the repository secrets by GitHub Actions.
    cargo("publish")
