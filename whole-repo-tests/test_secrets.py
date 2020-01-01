# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

import os

import pytest

import hypothesistooling as tools


@pytest.mark.skipif(
    os.environ.get("TRAVIS_SECURE_ENV_VARS", None) != "true",
    reason="Not running in an environment with travis secure vars",
)
def test_can_descrypt_secrets():
    tools.decrypt_secrets()

    assert os.path.exists(tools.DEPLOY_KEY)
