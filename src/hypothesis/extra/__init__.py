# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, unicode_literals

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
