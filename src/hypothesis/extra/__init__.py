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
from hypothesis.settings import Settings
from hypothesis.deprecation import note_deprecation


loaded = set()


def load_entry_points(name=None):
    for entry_point in pkg_resources.iter_entry_points(
        group='hypothesis.extra', name=name
    ):
        if entry_point.name in (
            'hypothesisdatetime', 'hypothesisdjango',
            'hypothesisfakefactory', 'hypothesisnumpy'
        ):
            base_name = entry_point.name.replace('hypothesis', '')

            note_deprecation(
                'Ignoring obsolete extra package hypothesis-%s. This '
                'functionality is now included in hypothesis core. You '
                'should uninstall the extra package.' % (base_name,),
                Settings.default
            )
            continue
        elif entry_point.name == 'hypothesispytest':
            note_deprecation(
                'You have an obsolete version of the hypothesis-pytest plugin '
                'installed. Please update to a more recent version.',
                Settings.default
            )
            continue
        else:
            note_deprecation(
                'The extra package mechanism is deprecated and will go away '
                "in Hypothesis 2.0. Just write a normal package and don't "
                'have it in the Hypothesis namespace.', Settings.default
            )
        package = entry_point.load()  # pragma: no cover
        if package not in loaded:
            loaded.add(package)
            __path__.extend(package.__path__)
            package.load()
