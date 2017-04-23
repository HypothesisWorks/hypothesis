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
import glob


def fixpath(p):
    p = os.path.abspath(p)
    if '*' in p:
        parts = glob.glob(p)
        if len(parts) != 1:
            print('Ambiguous path', p, file=sys.stderr)
            sys.exit(1)
        p = parts[0]
    return p


if __name__ == '__main__':
    _, source, target = sys.argv
    try:
        os.symlink(
            fixpath(source), fixpath(target)
        )
    except FileExistsError:
        pass
