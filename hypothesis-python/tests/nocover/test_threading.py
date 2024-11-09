# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import threading

from hypothesis import given, strategies as st


def test_can_run_given_in_thread():
    has_run_successfully = False

    @given(st.integers())
    def test(n):
        nonlocal has_run_successfully
        has_run_successfully = True

    t = threading.Thread(target=test)
    t.start()
    t.join()
    assert has_run_successfully
