# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import os
import subprocess
from glob import glob

import hypothesistooling as tools
import hypothesistooling.installers as install
import hypothesistooling.releasemanagement as rm
import hypothesistooling.projects.conjecturerust as cr
from hypothesistooling.junkdrawer import once, in_dir, unlink_if_present

PACKAGE_NAME = 'hypothesis-ruby'

HYPOTHESIS_RUBY = os.path.join(tools.ROOT, PACKAGE_NAME)

BASE_DIR = HYPOTHESIS_RUBY

TAG_PREFIX = PACKAGE_NAME + '-'

RELEASE_FILE = os.path.join(BASE_DIR, 'RELEASE.md')
CHANGELOG_FILE = os.path.join(BASE_DIR, 'CHANGELOG.md')
GEMSPEC_FILE = os.path.join(BASE_DIR, 'hypothesis-specs.gemspec')
CARGO_FILE = os.path.join(BASE_DIR, 'Cargo.toml')
CONJECTURE_CARGO_FILE = cr.CARGO_FILE

RUST_SRC = os.path.join(BASE_DIR, 'src')
RUBY_SRC = os.path.join(BASE_DIR, 'lib')


def has_release():
    """Is there a version of this package ready to release?"""
    return os.path.exists(RELEASE_FILE)


def parse_release_file():
    return rm.parse_release_file(RELEASE_FILE)


def update_changelog_and_version():
    """Update the changelog and version based on the current release file."""
    release_type, release_contents = parse_release_file()
    version = current_version()
    version_info = rm.parse_version(version)

    version, version_info = rm.bump_version_info(version_info, release_type)

    rm.replace_assignment(GEMSPEC_FILE, 's.version', repr(version))

    rm.update_markdown_changelog(
        CHANGELOG_FILE,
        name='Hypothesis for Ruby',
        version=version,
        entry=release_contents,
    )
    os.unlink(RELEASE_FILE)


LOCAL_PATH_DEPENDENCY = "{ path = '../conjecture-rust' }"


def update_conjecture_dependency(dependency):
    rm.replace_assignment(
        CARGO_FILE, 'conjecture',
        dependency
    )


def build_distribution():
    """Build the rubygem."""

    current_dependency = rm.extract_assignment(CARGO_FILE, 'conjecture')

    assert current_dependency == LOCAL_PATH_DEPENDENCY, (
        'Cargo file in a bad state. Expected conjecture dependency to be %s '
        'but it was instead %s'
    ) % (LOCAL_PATH_DEPENDENCY, current_dependency)

    conjecture_version = \
        rm.extract_assignment(CONJECTURE_CARGO_FILE, 'version')

    # Update to use latest version of conjecture-rust.
    try:
        update_conjecture_dependency(conjecture_version)
        rake_task('gem')
    finally:
        update_conjecture_dependency(LOCAL_PATH_DEPENDENCY)


def tag_name():
    """The tag name for the upcoming release."""
    return TAG_PREFIX + current_version()


def has_source_changes():
    """Returns True if any source files have changed."""
    return tools.has_changes([RUST_SRC, RUBY_SRC]) or cr.has_release()


def current_version():
    """Returns the current version as specified by the gemspec."""
    ensure_bundler()
    return subprocess.check_output([
        install.BUNDLER_EXECUTABLE, 'exec', 'ruby', '-e',
        RUBY_TO_PRINT_VERSION
    ]).decode('ascii').strip()


def bundle(*args):
    ensure_bundler()
    bundle_command(*args)


def bundle_command(*args):
    with in_dir(BASE_DIR):
        subprocess.check_call([
            install.BUNDLER_EXECUTABLE, *args
        ])


def rake_task(*args):
    bundle('exec', 'rake', *args)


@once
def ensure_bundler():
    install.ensure_rustup()
    install.ensure_ruby()
    bundle_command('install')


RUBY_TO_PRINT_VERSION = """
require 'rubygems'
spec = Gem::Specification::load(%r)
puts spec.version
""".strip().replace('\n', '; ') % (GEMSPEC_FILE,)


RUBYGEMS_CREDENTIALS = os.path.expanduser('~/.gem/credentials')


def upload_distribution():
    """Upload the built package to rubygems."""
    tools.assert_can_release()

    # Yes, rubygems really will only look in this file. Yes this is terrible.
    # This only runs on Travis, so we may be assumed to own it, but still.
    unlink_if_present(RUBYGEMS_CREDENTIALS)

    # symlink so that the actual secret credentials can't be leaked via the
    # cache.
    os.symlink(tools.RUBYGEMS_API_KEY, RUBYGEMS_CREDENTIALS)

    # Give the key the right permissions.
    os.chmod(RUBYGEMS_CREDENTIALS, int('0600', 8))

    subprocess.check_call([
        install.GEM_EXECUTABLE, 'push', *glob('hypothesis-specs-*.gem')
    ])
