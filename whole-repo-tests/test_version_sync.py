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
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

import toml

from hypothesistooling.projects.hypothesisruby import CARGO_FILE, GEMFILE_LOCK_FILE


def test_helix_version_sync():
    cargo = toml.load(CARGO_FILE)
    helix_version = cargo["dependencies"]["helix"]
    gem_lock = open(GEMFILE_LOCK_FILE).read()
    assert (
        "helix_runtime (%s)" % (helix_version,) in gem_lock
    ), "helix version must be the same in %s and %s" % (CARGO_FILE, GEMFILE_LOCK_FILE)
