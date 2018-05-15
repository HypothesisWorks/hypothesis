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
import re
import sys
import shlex
import subprocess
from datetime import datetime, timedelta


def current_branch():
    return subprocess.check_output([
        'git', 'rev-parse', '--abbrev-ref', 'HEAD'
    ]).decode('ascii').strip()


def tags():
    result = [t.decode('ascii') for t in subprocess.check_output([
        'git', 'tag'
    ]).split(b'\n')]
    assert len(set(result)) == len(result)
    return set(result)


ROOT = subprocess.check_output([
    'git', '-C', os.path.dirname(__file__), 'rev-parse', '--show-toplevel',
]).decode('ascii').strip()

HYPOTHESIS_PYTHON = os.path.join(ROOT, 'hypothesis-python')
HYPOTHESIS_RUBY = os.path.join(ROOT, 'hypothesis-ruby')

PYTHON_SRC = os.path.join(HYPOTHESIS_PYTHON, 'src')
PYTHON_TESTS = os.path.join(HYPOTHESIS_PYTHON, 'tests')

REPO_TESTS = os.path.join(ROOT, 'whole-repo-tests')

PYUP_FILE = os.path.join(ROOT, '.pyup.yml')


assert os.path.exists(PYTHON_SRC)


__version__ = None
__version_info__ = None

VERSION_FILE = os.path.join(PYTHON_SRC, 'hypothesis/version.py')

with open(VERSION_FILE) as o:
    exec(o.read())

assert __version__ is not None
assert __version_info__ is not None


PYTHON_TAG_PREFIX = 'hypothesis-python-'


def latest_version():
    versions = []

    for t in tags():
        if t.startswith(PYTHON_TAG_PREFIX):
            t = t[len(PYTHON_TAG_PREFIX):]
        else:
            continue
        assert t == t.strip()
        parts = t.split('.')
        assert len(parts) == 3
        v = tuple(map(int, parts))
        versions.append((v, t))

    _, latest = max(versions)

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


CHANGELOG_FILE = os.path.join(HYPOTHESIS_PYTHON, 'docs', 'changes.rst')


def changelog():
    with open(CHANGELOG_FILE) as i:
        return i.read()


def merge_base(a, b):
    return subprocess.check_output([
        'git', 'merge-base', a, b,
    ]).strip()


def point_of_divergence():
    return merge_base('HEAD', 'origin/master')


def has_changes(files):
    return subprocess.call([
        'git', 'diff', '--no-patch', '--exit-code', point_of_divergence(),
        'HEAD', '--', *files,
    ]) != 0


def has_python_source_changes():
    return has_changes([PYTHON_SRC])


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
        'git@github.com:HypothesisWorks/hypothesis.git'
    )
    git('tag', PYTHON_TAG_PREFIX + __version__)

    subprocess.check_call([
        'ssh-agent', 'sh', '-c',
        'ssh-add %s && ' % (shlex.quote(DEPLOY_KEY),) +
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
            point_of_divergence(), 'HEAD'],
        ['git', 'diff', '--name-only']
    ]:
        diff_output = subprocess.check_output(command).decode('ascii')
        for l in diff_output.split('\n'):
            filepath = l.strip()
            if filepath:
                assert os.path.exists(filepath), filepath
                files.add(filepath)
    return files


def all_files():
    return [
        f for f in subprocess.check_output(
            ['git', 'ls-files']).decode('ascii').splitlines()
        if os.path.exists(f)
    ]


RELEASE_FILE = os.path.join(HYPOTHESIS_PYTHON, 'RELEASE.rst')


def has_release():
    return os.path.exists(RELEASE_FILE)


CHANGELOG_ANCHOR = re.compile(r"^\.\. _v\d+\.\d+\.\d+:$")
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
        if CHANGELOG_ANCHOR.match(l):
            assert CHANGELOG_BORDER.match(lines[i + 2]), repr(lines[i + 2])
            assert CHANGELOG_HEADER.match(lines[i + 3]), repr(lines[i + 3])
            assert CHANGELOG_BORDER.match(lines[i + 4]), repr(lines[i + 4])
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
        '.. _v%s:' % (new_version_string),
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
        'commit', '-m',
        'Bump version to %s and update changelog\n\n[skip ci]' % (__version__,)
    )


def changed_files_from_master():
    """Returns a list of files which have changed between a branch and
    master."""
    files = set()
    command = ['git', 'diff', '--name-only', 'HEAD', 'master']
    diff_output = subprocess.check_output(command).decode('ascii')
    for line in diff_output.splitlines():
        filepath = line.strip()
        if filepath:
            files.add(filepath)
    return files


SECRETS_BASE = os.path.join(ROOT, 'secrets')
SECRETS_TAR = SECRETS_BASE + '.tar'
ENCRYPTED_SECRETS = SECRETS_TAR + '.enc'

DEPLOY_KEY = os.path.join(ROOT, 'deploy_key')
PYPIRC = os.path.join(ROOT, '.pypirc')


def decrypt_secrets():
    subprocess.check_call([
        'openssl', 'aes-256-cbc',
        '-K', os.environ['encrypted_39cb4cc39a80_key'],
        '-iv', os.environ['encrypted_39cb4cc39a80_iv'],
        '-in', ENCRYPTED_SECRETS,
        '-out', SECRETS_TAR,
        '-d'
    ])

    subprocess.check_call(['tar', '-xvf', SECRETS_TAR], cwd=ROOT)
    assert os.path.exists(DEPLOY_KEY)
    assert os.path.exists(PYPIRC)
    os.chmod(DEPLOY_KEY, int('0600', 8))


IS_TRAVIS_PULL_REQUEST = (
    os.environ.get('TRAVIS_EVENT_TYPE') == 'pull_request'
)

IS_CIRCLE_PULL_REQUEST = (
    os.environ.get('CIRCLE_BRANCH') == 'master' and
    os.environ.get('CI_PULL_REQUESTS', '') != ''
)


IS_PULL_REQUEST = IS_TRAVIS_PULL_REQUEST or IS_CIRCLE_PULL_REQUEST
