# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
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

import pytest

from tests.array_api.common import COMPLIANT_XP, MOCK_WARN_MSG


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "mockable_xp: mocked array module possibly used in test"
    )


def pytest_collection_modifyitems(config, items):
    if not COMPLIANT_XP:
        mark = pytest.mark.filterwarnings(f"ignore:.*{MOCK_WARN_MSG}.*")
        for item in items:
            if "mockable_xp" in item.keywords:
                item.add_marker(mark)
