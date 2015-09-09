# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

import pkg_resources
from hypothesis.settings import Settings
from hypothesis.deprecation import note_deprecation


loaded = set()


def load_entry_points(name=None):
    for entry_point in pkg_resources.iter_entry_points(
        group=u'hypothesis.extra', name=name
    ):
        if entry_point.name in (
            u'hypothesisdatetime', u'hypothesisdjango',
            u'hypothesisfakefactory', u'hypothesisnumpy'
        ):
            base_name = entry_point.name.replace(u'hypothesis', u'')

            note_deprecation(
                u'Ignoring obsolete extra package hypothesis-%s. This '
                u'functionality is now included in hypothesis core. You '
                u'should uninstall the extra package.' % (base_name,),
                Settings.default
            )
            continue
        elif entry_point.name == u'hypothesispytest':
            note_deprecation(
                u'You have an obsolete version of the hypothesis-pytest '
                u'plugin installed. Please update to a more recent version.',
                Settings.default
            )
            continue
        else:
            note_deprecation(
                u'The extra package mechanism is deprecated and will go away '
                u"in Hypothesis 2.0. Just write a normal package and don't "
                u'have it in the Hypothesis namespace.', Settings.default
            )
        package = entry_point.load()  # pragma: no cover
        if package not in loaded:
            loaded.add(package)
            __path__.extend(package.__path__)
            package.load()
