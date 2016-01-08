# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import sys

from hypothesis._settings import settings as RealSettings
from hypothesis._settings import Settings, note_deprecation, \
    storage_directory, hypothesis_home_dir, set_hypothesis_home_dir

__all__ = [
    'hypothesis_home_dir', 'set_hypothesis_home_dir',
    'storage_directory', 'Settings',
]

note_deprecation(
    'The hypothesis.settings module has been split up. Import the settings '
    'type directly from the Hypothesis package. Other functionality has moved '
    'to hypothesis.configuration.'
)

sys.modules['hypothesis.settings'] = RealSettings
