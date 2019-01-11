# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

import inspect
import os
import sys
import warnings
from tempfile import mkdtemp

import unicodenazi

from hypothesis import settings, unlimited
from hypothesis.configuration import set_hypothesis_home_dir
from hypothesis.errors import HypothesisDeprecationWarning

warnings.filterwarnings("error", category=UnicodeWarning)
warnings.filterwarnings("error", category=HypothesisDeprecationWarning)
unicodenazi.enable()


set_hypothesis_home_dir(mkdtemp())

assert isinstance(settings, type)

settings.register_profile("default", settings(timeout=unlimited))
settings.load_profile("default")


TESTS = ["test_testdecorators"]

sys.path.append(os.path.join("tests", "cover"))


def main():
    for t in TESTS:
        module = __import__(t)
        for k, v in sorted(module.__dict__.items(), key=lambda x: x[0]):
            if k.startswith("test_") and inspect.isfunction(v):
                print(k)
                v()


if __name__ == "__main__":
    main()
