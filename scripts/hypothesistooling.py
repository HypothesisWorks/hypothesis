# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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
import re
import sys
import subprocess
from datetime import datetime, timedelta


def current_branch():
    return subprocess.check_output([
        'git', 'rev-parse', '--abbrev-ref', 'HEAD'
    ]).decode('ascii').strip()


def tags():
    result = [t.decode('ascii') for t in subprocess.check_output([
        'git', 'tag'
    ]).split(b"\n")]
    assert len(set(result)) == len(result)
    return set(result)


ROOT = subprocess.check_output([
    'git', 'rev-parse', '--show-toplevel']).decode('ascii').strip()
SRC = os.path.join(ROOT, 'src')

assert os.path.exists(SRC)


__version__ = None
__version_info__ = None

VERSION_FILE = os.path.join(ROOT, 'src/hypothesis/version.py')

with open(VERSION_FILE) as o:
    exec(o.read())

assert __version__ is not None
assert __version_info__ is not None


def latest_version():
    versions = []

    for t in tags():
        # All versions get tags but not all tags are versions (and there are
        # a large number of historic tags with a different format for versions)
        # so we parse each tag as a triple of ints (MAJOR, MINOR, PATCH)
        # and skip any tag that doesn't match that.
        assert t == t.strip()
        parts = t.split('.')
        if len(parts) != 3:
            continue
        try:
            v = tuple(map(int, parts))
        except ValueError:
            continue

        versions.append((v, t))

    _, latest = max(versions)

    assert latest in tags()
    return latest


def hash_for_name(name):
    return subprocess.check_output([
        'git', 'rev-parse', name
    ]).decode('ascii').strip()


def is_ancestor(a, b):
    check = subprocess.call([
        'git', 'merge-base', '--is-ancestor', a, b
    ])
    assert 0 <= check <= 1
    return check == 0


CHANGELOG_FILE = os.path.join(ROOT, 'docs', 'changes.rst')


def changelog():
    with open(CHANGELOG_FILE) as i:
        return i.read()


def merge_base(a, b):
    return subprocess.check_output([
        'git', 'merge-base', a, b,
    ]).strip()


def has_source_changes(version=None):
    if version is None:
        version = latest_version()

    # Check where we branched off from the version. We're only interested
    # in whether *we* introduced any source changes, so we check diff from
    # there rather than the diff to the other side.
    point_of_divergence = merge_base('HEAD', version)

    return subprocess.call([
        'git', 'diff', '--exit-code', point_of_divergence, 'HEAD', '--', SRC,
    ]) != 0


def has_uncommitted_changes(filename):
    return subprocess.call([
        'git', 'diff', '--exit-code', filename
    ]) != 0


def git(*args):
    subprocess.check_call(('git',) + args)


def create_tag_and_push():
    assert __version__ not in tags()
    git('config', 'user.name', 'Travis CI on behalf of David R. MacIver')
    git('config', 'user.email', 'david@drmaciver.com')
    git('config', 'core.sshCommand', 'ssh -i deploy_key')
    git(
        'remote', 'add', 'ssh-origin',
        'git@github.com:HypothesisWorks/hypothesis-python.git'
    )
    git('tag', __version__)

    subprocess.check_call([
        'ssh-agent', 'sh', '-c',
        'chmod 0600 deploy_key && ' +
        'ssh-add deploy_key && ' +
        'git push ssh-origin HEAD:master &&'
        'git push ssh-origin --tags'
    ])


def build_jobs():
    """Query the Travis API to find out what the state of the other build jobs
    is.

    Note: This usage of Travis has been somewhat reverse engineered due
    to a certain dearth of documentation as to what values what takes
    when.

    """
    import requests

    build_id = os.environ['TRAVIS_BUILD_ID']

    url = 'https://api.travis-ci.org/builds/%s' % (build_id,)
    data = requests.get(url, headers={
        'Accept': 'application/vnd.travis-ci.2+json'
    }).json()

    matrix = data['jobs']

    jobs = {}

    for m in matrix:
        name = m['config']['env'].replace('TASK=', '')
        status = m['state']
        jobs.setdefault(status, []).append(name)
    return jobs


def modified_files():
    files = set()
    for command in [
        ['git', 'diff', '--name-only', '--diff-filter=d',
            latest_version(), 'HEAD'],
        ['git', 'diff', '--name-only']
    ]:
        diff_output = subprocess.check_output(command).decode('ascii')
        for l in diff_output.split('\n'):
            filepath = l.strip()
            if filepath:
                assert os.path.exists(filepath)
                files.add(filepath)
    return files


def all_files():
    return subprocess.check_output(['git', 'ls-files']).decode(
        'ascii').splitlines()


RELEASE_FILE = os.path.join(ROOT, 'RELEASE.rst')


def has_release():
    return os.path.exists(RELEASE_FILE)


CHANGELOG_BORDER = re.compile(r"^-+$")
CHANGELOG_HEADER = re.compile(r"^\d+\.\d+\.\d+ - \d\d\d\d-\d\d-\d\d$")
RELEASE_TYPE = re.compile(r"^RELEASE_TYPE: +(major|minor|patch)")


MAJOR = 'major'
MINOR = 'minor'
PATCH = 'patch'

VALID_RELEASE_TYPES = (MAJOR, MINOR, PATCH)


def parse_release_file():
    with open(RELEASE_FILE) as i:
        release_contents = i.read()

    release_lines = release_contents.split('\n')

    m = RELEASE_TYPE.match(release_lines[0])
    if m is not None:
        release_type = m.group(1)
        if release_type not in VALID_RELEASE_TYPES:
            print('Unrecognised release type %r' % (release_type,))
            sys.exit(1)
        del release_lines[0]
        release_contents = '\n'.join(release_lines).strip()
    else:
        print(
            'RELEASE.rst does not start by specifying release type. The first '
            'line of the file should be RELEASE_TYPE: followed by one of '
            'major, minor, or patch, to specify the type of release that '
            'this is (i.e. which version number to increment). Instead the '
            'first line was %r' % (release_lines[0],)
        )
        sys.exit(1)

    return release_type, release_contents


def update_changelog_and_version():
    global __version_info__
    global __version__

    with open(CHANGELOG_FILE) as i:
        contents = i.read()
    assert '\r' not in contents
    lines = contents.split('\n')
    assert contents == '\n'.join(lines)
    for i, l in enumerate(lines):
        if CHANGELOG_BORDER.match(l):
            assert CHANGELOG_HEADER.match(lines[i + 1]), repr(lines[i + 1])
            assert CHANGELOG_BORDER.match(lines[i + 2]), repr(lines[i + 2])
            beginning = '\n'.join(lines[:i])
            rest = '\n'.join(lines[i:])
            assert '\n'.join((beginning, rest)) == contents
            break

    release_type, release_contents = parse_release_file()

    new_version = list(__version_info__)
    bump = VALID_RELEASE_TYPES.index(release_type)
    new_version[bump] += 1
    for i in range(bump + 1, len(new_version)):
        new_version[i] = 0
    new_version = tuple(new_version)
    new_version_string = '.'.join(map(str, new_version))

    __version_info__ = new_version
    __version__ = new_version_string

    with open(VERSION_FILE) as i:
        version_lines = i.read().split('\n')

    for i, l in enumerate(version_lines):
        if 'version_info' in l:
            version_lines[i] = '__version_info__ = %r' % (new_version,)
            break

    with open(VERSION_FILE, 'w') as o:
        o.write('\n'.join(version_lines))

    now = datetime.utcnow()

    date = max([
        d.strftime('%Y-%m-%d') for d in (now, now + timedelta(hours=1))
    ])

    heading_for_new_version = ' - '.join((new_version_string, date))
    border_for_new_version = '-' * len(heading_for_new_version)

    new_changelog_parts = [
        beginning.strip(),
        '',
        border_for_new_version,
        heading_for_new_version,
        border_for_new_version,
        '',
        release_contents,
        '',
        rest
    ]

    with open(CHANGELOG_FILE, 'w') as o:
        o.write('\n'.join(new_changelog_parts))


def update_for_pending_release():
    update_changelog_and_version()

    git('rm', RELEASE_FILE)
    git('add', CHANGELOG_FILE, VERSION_FILE)

    git(
        'commit',
        '-m', 'Bump version to %s and update changelog' % (__version__,)
    )
