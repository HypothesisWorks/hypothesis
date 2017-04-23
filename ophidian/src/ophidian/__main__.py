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

import click
from ophidian.core import Ophidian, NoSuchPython
from ophidian.finder import default_paths
from ophidian.storage import DirStorage
from ophidian.installer import PyenvInstaller


@click.command()
@click.option('--major', type=int, default=None)
@click.option('--minor', type=int, default=None)
@click.option('--micro', type=int, default=None)
@click.option('--implementation', type=str, default=None)
@click.option('--identifier', type=str, default=None)
@click.option('--install/--no-install', default=True)
def main(major, minor, micro, install, implementation, identifier):
    homedir = os.environ['OPHIDIAN_HOME']

    builds = os.path.join(homedir, 'builds')

    try:
        os.makedirs(builds)
    except FileExistsError:
        pass

    if identifier is not None:
        if any(c is not None for c in [major, minor, micro, implementation]):
            raise click.UsageError(
                'Other query options are not compatible with --implementation'
            )

    if implementation is not None:
        implementation = implementation.lower()

    if implementation not in [None, 'cpython', 'pypy']:
        raise click.UsageError(
            'Unsuported implementation %r' % (implementation,))

    cache = os.path.join(homedir, 'cache')
    try:
        os.makedirs(cache)
    except FileExistsError:
        pass

    paths = list(default_paths())
    paths.insert(0, builds)

    ophidian = Ophidian(
        cache=DirStorage(cache), paths=paths,
        installer=PyenvInstaller(
            pyenv_root=os.environ['OPHIDIAN_PYENV'],
            installation_directory=builds,
        )
    )

    try:
        found = ophidian.get_python(
            major=major, minor=minor, micro=micro,
            implementation=implementation,
            identifier=identifier,
        )
        click.echo(found.path)
    except NoSuchPython:
        click.echo(
            'No such Python installed and --no-install is set', err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
