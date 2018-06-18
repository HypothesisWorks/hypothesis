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
import shlex
import subprocess


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

HYPOTHESIS_RUBY = os.path.join(ROOT, 'hypothesis-ruby')

REPO_TESTS = os.path.join(ROOT, 'whole-repo-tests')

PYUP_FILE = os.path.join(ROOT, '.pyup.yml')


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


def has_uncommitted_changes(filename):
    return subprocess.call([
        'git', 'diff', '--exit-code', filename
    ]) != 0


def git(*args):
    subprocess.check_call(('git',) + args)


def configure_git():
    git('config', 'user.name', 'Travis CI on behalf of David R. MacIver')
    git('config', 'user.email', 'david@drmaciver.com')
    git('config', 'core.sshCommand', 'ssh -i deploy_key')
    git(
        'remote', 'add', 'ssh-origin',
        'git@github.com:HypothesisWorks/hypothesis.git'
    )


def create_tag(tagname):
    assert tagname not in tags()
    git('tag', tagname)


def push_tag(tagname):
    subprocess.check_call([
        'ssh-agent', 'sh', '-c',
        'ssh-add %s && ' % (shlex.quote(DEPLOY_KEY),) +
        'git push ssh-origin HEAD:master &&' +
        'git push ssh-origin %s' % (shlex.quote(tagname),)
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

SECRETS = os.path.join(ROOT, 'secrets')

DEPLOY_KEY = os.path.join(SECRETS, 'deploy_key')
PYPIRC = os.path.join(SECRETS, '.pypirc')


def decrypt_secrets():
    subprocess.check_call([
        'openssl', 'aes-256-cbc',
        '-K', os.environ['encrypted_b8618e5d043b_key'],
        '-iv', os.environ['encrypted_b8618e5d043b_iv'],
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


def all_projects():
    import hypothesistooling.projects.hypothesispython as hp
    return [hp]
