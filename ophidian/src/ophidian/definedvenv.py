#!/usr/bin/env python

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
import sys
import shutil
import hashlib
import binascii
import subprocess


def fail(*args):
    print(*args, file=sys.stderr)
    sys.exit(1)


PY3 = sys.version_info[0]


def sha1(s):
    if PY3:
        s = s.encode('utf-8')
    return hashlib.sha1(s).hexdigest()


def call_or_die(*args, **kwargs):
    kwargs['stdout'] = sys.stderr
    result = subprocess.call(*args, **kwargs)
    if result != 0:
        sys.exit(result)


def randhex():
    result = binascii.hexlify(os.urandom(16))
    if PY3:
        result = result.decode('ascii')
    return result


if __name__ == '__main__':

    if len(sys.argv) != 3:
        fail('Usage: defined-env.py requirements target-dir')

    _, requirements, target = sys.argv

    if not os.path.exists(requirements):
        fail('No such file', requirements)

    try:
        import virtualenv  # noqas
    except ImportError as e:
        if 'virtualenv' not in e.args[0]:
            raise
        fail('virtualenv is not installed')

    with open(requirements) as i:
        requirements_data = i.read()

    requirements_set = set(requirements_data.split('\n'))

    try:
        os.makedirs(target)
    except FileExistsError:
        pass

    name = os.path.basename(requirements).split(os.path.extsep)[0]

    virtualenv_name = (
        '%(implementation)s%(major)d.%(minor)d.%(micro)d-%(name)s-%(hash)s'
    ) % {
        'implementation': sys.implementation.name,
        'major': sys.version_info[0],
        'minor': sys.version_info[1],
        'micro': sys.version_info[2],
        'name': name,
        'hash': sha1(requirements_data)[:8],
    }

    target_venv = os.path.join(target, virtualenv_name)
    target_python = os.path.join(target_venv, 'bin', 'python')

    def build_virtualenv():
        assert not os.path.exists(target_venv)
        try:
            call_or_die([
                sys.executable, '-m', 'virtualenv', target_venv
            ])

            call_or_die([
                target_python, '-m', 'pip', 'install', '--upgrade',
                'pip', 'setuptools', 'wheel',
            ])
            call_or_die([
                target_python, '-m', 'pip', 'install',
                '-r', requirements
            ])
        except BaseException:
            if os.path.exists(target_venv):
                shutil.rmtree(target_venv)
            raise

    if not os.path.exists(target_venv):
        build_virtualenv()

    assert os.path.exists(target_venv)

    def missing_requirements():
        installed = set(subprocess.check_output([
            target_python, '-m', 'pip', 'freeze'
        ]).decode('ascii').split('\n'))

        return requirements_set - installed

    initially_missing = missing_requirements()
    if initially_missing:
        print(
            'Reinstalling due to missing requirement%s: %s' % (
                's' if len(missing_requirements) > 1 else '',
                ', '.join(sorted(missing_requirements)),
            ), file=sys.stderr
        )
        shutil.rmtree(virtualenv)
        build_virtualenv()
        still_missing = missing_requirements()
        if still_missing:
            fail((
                "Something is going wrong: After reinstallation we're still "
                'missing %s') % (
                    ', '.join(sorted(still_missing),)))

    print(target_venv)
