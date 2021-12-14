# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import given
from hypothesis.strategies import emails


@given(emails())
def test_is_valid_email(address):
    local, at_, domain = address.rpartition("@")
    assert len(address) <= 254
    assert at_ == "@"
    assert local
    assert domain
