# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

from hypothesis import settings
from hypothesis.configuration import set_hypothesis_home_dir
from hypothesis.internal.charmap import charmap, charmap_file


def run():
    warnings.filterwarnings(u'error', category=UnicodeWarning)

    set_hypothesis_home_dir(mkdtemp())

    charmap()
    assert os.path.exists(charmap_file())
    assert isinstance(settings, type)

    settings.register_profile(
        'default', settings(timeout=-1, strict=True)
    )

    settings.register_profile(
        'speedy', settings(
            timeout=1, max_examples=5,
        ))

    settings.register_profile(
        'nonstrict', settings(strict=False)
    )

    settings.load_profile(os.getenv('HYPOTHESIS_PROFILE', 'default'))
