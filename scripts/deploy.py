#!/usr/bin/env python

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
import sys
import random
import shutil
import subprocess
from time import time, sleep

import hypothesistooling as tools

sys.path.append(os.path.dirname(__file__))  # noqa


DIST = os.path.join(tools.ROOT, 'dist')


PENDING_STATUS = ('started', 'created')


if __name__ == '__main__':
    last_release = tools.latest_version()

    print('Current version: %s. Latest released version: %s' % (
        tools.__version__, last_release
    ))

    HEAD = tools.hash_for_name('HEAD')
    MASTER = tools.hash_for_name('origin/master')
    print('Current head:', HEAD)
    print('Current master:', MASTER)

    on_master = tools.is_ancestor(HEAD, MASTER)
    has_release = tools.has_release()

    if has_release:
        print('Updating changelog and version')
        tools.update_for_pending_release()

    print('Building an sdist...')

    if os.path.exists(DIST):
        shutil.rmtree(DIST)

    subprocess.check_output([
        sys.executable, 'setup.py', 'sdist', '--dist-dir', DIST,
    ])

    if not on_master:
        print('Not deploying due to not being on master')
        sys.exit(0)

    if not has_release:
        print('Not deploying due to no release')
        sys.exit(0)

    print('Looks good to release!')

    if os.environ.get('TRAVIS_SECURE_ENV_VARS', None) != 'true':
        print("But we don't have the keys to do it")
        sys.exit(0)

    print('Decrypting secrets')

    # We'd normally avoid the use of shell=True, but this is more or less
    # intended as an opaque string that was given to us by Travis that happens
    # to be a shell command that we run, and there are a number of good reasons
    # this particular instance is harmless and would be high effort to
    # convert (principally: Lack of programmatic generation of the string and
    # extensive use of environment variables in it), so we're making an
    # exception here.
    subprocess.check_call(
        'openssl aes-256-cbc -K $encrypted_39cb4cc39a80_key '
        '-iv $encrypted_39cb4cc39a80_iv -in secrets.tar.enc '
        '-out secrets.tar -d',
        shell=True
    )

    subprocess.check_call([
        'tar', '-xvf', 'secrets.tar',
    ])

    print('Release seems good. Pushing to github now.')

    tools.create_tag_and_push()

    print('Now uploading to pypi.')

    subprocess.check_call([
        sys.executable, '-m', 'twine', 'upload',
        '--config-file', './.pypirc',
        os.path.join(DIST, '*'),
    ])

    sys.exit(0)
