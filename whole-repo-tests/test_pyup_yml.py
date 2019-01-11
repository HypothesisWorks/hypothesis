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

import yaml
from pyup.config import Config

import hypothesistooling as tools


def test_pyup_yml_is_valid():
    with open(tools.PYUP_FILE, "r") as i:
        data = yaml.safe_load(i.read())
    config = Config()
    config.update_config(data)

    assert config.is_valid_schedule(), "Schedule %r is invalid" % (config.schedule,)
