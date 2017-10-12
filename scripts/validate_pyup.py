#!/usr/bin/env python

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

from hypothesistooling import ROOT
import yaml
from pyup.config import Config
import os
import sys


PYUP_FILE = os.path.join(ROOT, ".pyup.yml")

if __name__ == '__main__':
    with open(PYUP_FILE, 'r') as i:
        data = yaml.safe_load(i.read())
    config = Config()
    config.update_config(data)

    if not config.is_valid_schedule():
        print("Schedule %r is invalid" % (config.schedule,))
        sys.exit(1)
