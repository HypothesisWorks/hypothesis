# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import black
import pytest
from black.parsing import InvalidInput

from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.observability import make_testcase


def test_make_testcase_invalid_representation():
    # we fall back to the representation if black fails to parse
    invalid_representation = "class"

    with pytest.raises(InvalidInput):
        black.format_str(invalid_representation, mode=black.Mode())

    data = ConjectureData.for_choices([])
    data.freeze()
    tc = make_testcase(
        run_start=0,
        property="test_f",
        data=data,
        how_generated="",
        representation="class",
        timing={},
    )
    assert tc.representation == invalid_representation
