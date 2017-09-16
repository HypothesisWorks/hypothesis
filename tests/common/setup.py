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
import warnings
from tempfile import mkdtemp

from hypothesis import settings, unlimited
from hypothesis.errors import HypothesisDeprecationWarning
from hypothesis.configuration import set_hypothesis_home_dir
from hypothesis.internal.charmap import charmap, charmap_file


def run():
    warnings.filterwarnings('error', category=UnicodeWarning)
    warnings.filterwarnings('error', category=HypothesisDeprecationWarning)

    set_hypothesis_home_dir(mkdtemp())

    charmap()
    assert os.path.exists(charmap_file()), charmap_file()
    assert isinstance(settings, type)

    # We do a smoke test here before we mess around with settings.
    x = settings()

    import hypothesis._settings as settings_module

    for s in settings_module.all_settings.values():
        v = getattr(x, s.name)
        # Check if it has a dynamically defined default and if so skip
        # comparison.
        if getattr(settings, s.name).show_default:
            assert v == s.default, '%r == x.%s != s.%s == %r' % (
                v, s.name, s.name, s.default,
            )

    settings.register_profile('default', settings(timeout=unlimited))

    settings.register_profile(
        'speedy', settings(
            max_examples=5,
        ))

    settings.load_profile(os.getenv('HYPOTHESIS_PROFILE', 'default'))
