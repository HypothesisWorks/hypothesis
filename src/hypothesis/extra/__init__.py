# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pkg_resources


loaded = set()


def load_entry_points(name=None):
    for entry_point in pkg_resources.iter_entry_points(
        group='hypothesis.extra', name=name
    ):
        package = entry_point.load()  # pragma: no cover
        if package not in loaded:
            loaded.add(package)
            __path__.extend(package.__path__)
            package.load()
