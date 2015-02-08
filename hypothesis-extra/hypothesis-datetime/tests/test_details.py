# coding=utf-8

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function, unicode_literals

# END HEADER

import random
from hypothesisdatetime import draw_day_for_month
import pytest


def test_draw_day_for_month_errors_on_bad_month():
    with pytest.raises(ValueError):
        draw_day_for_month(random, 2001, 13)
