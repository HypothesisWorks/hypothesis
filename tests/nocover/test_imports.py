# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import *
from hypothesis.strategies import *


def test_can_star_import_from_hypothesis():
    find(
        lists(integers()),
        lambda x: sum(x) > 1,
        settings=settings(max_examples=10000, verbosity=Verbosity.quiet),
    )
