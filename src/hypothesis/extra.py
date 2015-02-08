# coding=utf-8

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function, unicode_literals, division

# END HEADER

import pkg_resources


def load_entry_points():
    for entry_point in pkg_resources.iter_entry_points(
        group='hypothesis.extra'
    ):
        entry_point.load()()  # pragma: no cover
