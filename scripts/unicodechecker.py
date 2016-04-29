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

import warnings
from tempfile import mkdtemp
import unicodenazi

warnings.filterwarnings('error', category=UnicodeWarning)
unicodenazi.enable()

from hypothesis import settings
from hypothesis.configuration import set_hypothesis_home_dir

set_hypothesis_home_dir(mkdtemp())

assert isinstance(settings, type)

settings.register_profile(
    'default', settings(timeout=-1, strict=True)
)
settings.load_profile('default')

import inspect
import os


TESTS = [
    'test_testdecorators',
]

import sys
sys.path.append(os.path.join(
    os.path.dirname(__file__), "..", "tests", "cover",
))

if __name__ == '__main__':
    for t in TESTS:
        module = __import__(t)
        for k, v in sorted(module.__dict__.items(), key=lambda x: x[0]):
            if k.startswith("test_") and inspect.isfunction(v):
                print(k)
                v()
