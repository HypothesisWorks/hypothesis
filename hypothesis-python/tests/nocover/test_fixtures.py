# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import time

from tests.common import TIME_INCREMENT


def test_time_consistently_increments_in_tests():
    x = time.time()
    y = time.time()
    z = time.time()
    assert y == x + TIME_INCREMENT
    assert z == y + TIME_INCREMENT
