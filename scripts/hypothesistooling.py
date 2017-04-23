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
import subprocess


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


with open(os.path.join(ROOT, 'src/hypothesis/version.py')) as o:
    exec(o.read())

assert __version__ is not None


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


def on_master():
    return hash_for_name('HEAD') == hash_for_name('origin/master')


def changelog():
    with open(os.path.join(ROOT, 'docs', 'changes.rst')) as i:
        return i.read()


def has_source_changes(version):
    # Check where we branched off from the version. We're only interested
    # in whether *we* introduced any source changes, so we check diff from
    # there rather than the diff to the other side.
    point_of_divergence = subprocess.check_output([
        "git", "merge-base", "HEAD", version
    ])

    return subprocess.call([
        'git', 'diff', '--exit-code', point_of_divergence, SRC,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0


def git(*args):
    subprocess.check_call(('git',) + args)


def create_tag():
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
