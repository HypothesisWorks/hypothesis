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
from hypothesistooling import git
from hypothesistooling.junkdrawer import once, in_dir

PACKAGE_NAME = 'hypothesis-ruby'

HYPOTHESIS_RUBY = os.path.join(tools.ROOT, PACKAGE_NAME)

BASE_DIR = HYPOTHESIS_RUBY

TAG_PREFIX = PACKAGE_NAME + '-'

RELEASE_FILE = os.path.join(BASE_DIR, 'RELEASE.md')
CHANGELOG_FILE = os.path.join(BASE_DIR, 'CHANGELOG.md')
GEMSPEC_FILE = os.path.join(BASE_DIR, 'hypothesis-specs.gemspec')

RUST_SRC = os.path.join(BASE_DIR, 'src')
RUBY_SRC = os.path.join(BASE_DIR, 'lib')


def has_release():
    """Is there a version of this package ready to release?"""
    return os.path.exists(RELEASE_FILE)


def update_changelog_and_version():
    """Update the changelog and version based on the current release file."""
    rake_task('update_changelog_and_version')


def commit_pending_release():
    """Create a commit with the new release."""
    git('rm', RELEASE_FILE)
    git('add', CHANGELOG_FILE, GEMSPEC_FILE)

    git(
        'commit', '-m',
        'Bump hypothesis-ruby version to %s and update changelog'
        '\n\n[skip ci]' % (current_version(),)
    )


def build_distribution():
    """Build the rubygem."""
    rake_task('gem')


def tag_name():
    """The tag name for the upcoming release."""
    return TAG_PREFIX + current_version()


def has_source_changes():
    """Returns True if any source files have changed."""
    return tools.has_changes([RUST_SRC, RUBY_SRC])


def current_version():
    """Returns the current version as specified by the gemspec."""
    ensure_bundler()
    return subprocess.check_output([
        install.BUNDLER_EXECUTABLE, 'exec', 'ruby', '-e',
        RUBY_TO_PRINT_VERSION
    ]).decode('ascii').strip()


def bundle(*args):
    install.ensure_rustup()
    install.ensure_ruby()
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
    os.path.unlink(RUBYGEMS_CREDENTIALS)

    # symlink so that the actual secret credentials can't be leaked via the
    # cache.
    os.symlink(tools.RUBYGEMS_API_KEY, RUBYGEMS_CREDENTIALS)

    # Give the key the right permissions.
    os.chmod(tools.RUBYGEMS_CREDENTIALS, int('0600', 8))

    subprocess.check_call([
        install.GEM_EXECUTABLE, 'push', *glob('hypothesis-specs-*.gem')
    ])
