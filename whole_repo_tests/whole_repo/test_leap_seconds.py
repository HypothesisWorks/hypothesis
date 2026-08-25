# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import datetime as dt

from hypothesis.strategies._internal.datetime import _LEAP_SECONDS
from hypothesistooling.release import PYTHON_SRC


def test_leap_seconds_literal_matches_vendored_list():
    # The vendored IERS file is a repo-only reference, refreshed by
    # `update_vendored_files`; if it gains an entry, add it to the
    # _LEAP_SECONDS literal too.
    source = PYTHON_SRC / "hypothesis" / "vendor" / "leap-seconds.list"
    epoch = dt.datetime(1900, 1, 1)  # the NTP epoch used for the timestamps
    parsed = tuple(
        epoch + dt.timedelta(seconds=int(line.split()[0]))
        for line in source.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    )
    assert parsed == _LEAP_SECONDS
