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

import click
from ophidian.core import Ophidian
from ophidian.storage import DirStorage


@click.command()
@click.option('--major', type=int, default=None)
@click.option('--minor', type=int, default=None)
@click.option('--micro', type=int, default=None)
@click.option('--install/--no-install', default=True)
def main(major, minor, micro, install):
    homedir = os.environ['OPHIDIAN_HOME']

    cache = os.path.join(homedir, 'cache')
    try:
        os.makedirs(cache)
    except FileExistsError:
        pass

    ophidian = Ophidian(cache=DirStorage(cache))

    def predicate(python):
        if major is not None and python.version[0] != major:
            return False
        if minor is not None and python.version[1] != minor:
            return False
        if micro is not None and python.version[2] != micro:
            return False
        return True
    click.echo(ophidian.find_python(predicate).path)


if __name__ == '__main__':
    main()
