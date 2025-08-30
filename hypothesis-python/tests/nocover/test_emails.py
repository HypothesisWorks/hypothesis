# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis import given, settings
from hypothesis.strategies import emails, just


@pytest.mark.skipif(
    settings._current_profile == "crosshair",
    reason="takes ~7 mins; first barrier: the `sampled_from(get_top_level_domains())` decision is "
    "realized via iterative comparisons; see https://github.com/pschanely/CrossHair/issues/332",
)
@given(emails())
def test_is_valid_email(address: str):
    local, at_, domain = address.rpartition("@")
    assert len(address) <= 254
    assert at_ == "@"
    assert local
    assert domain
    assert not domain.lower().endswith(".arpa")


@given(emails(domains=just("mydomain.com")))
def test_can_restrict_email_domains(address: str):
    assert address.endswith("@mydomain.com")
