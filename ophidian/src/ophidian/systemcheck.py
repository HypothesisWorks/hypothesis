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

import sys
import json

try:
    implementation = sys.implementation.name
except AttributeError:
    implementation = sys.subversion[0]


def calc_max_size():
    i = sys.maxsize
    k = 0
    while i > 0:
        k += 8
        i >>= 8
    return k


checks = {
    'version': list(sys.version_info[:3]),
    'implementation': implementation,
    'wordsize': calc_max_size(),
}


if sys.version_info[0] == 2:
    checks['wide'] = sys.maxunicode == 1114111
else:
    checks['wide'] = True

if __name__ == '__main__':
    print(json.dumps(checks))
