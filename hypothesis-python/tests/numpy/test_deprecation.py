# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from warnings import catch_warnings

import pytest

from hypothesis.errors import HypothesisDeprecationWarning, InvalidArgument
from hypothesis.extra import numpy as nps

from tests.common.debug import check_can_generate_examples


def test_basic_indices_bad_min_dims_warns():
    with pytest.warns(HypothesisDeprecationWarning):
        # NOTE: For compatibility with Python 3.9's LL(1)
        # parser, this is written as a nested with-statement,
        # instead of a compound one.
        with pytest.raises(InvalidArgument):
            check_can_generate_examples(nps.basic_indices((3, 3, 3), min_dims=4))


def test_basic_indices_bad_max_dims_warns():
    with pytest.warns(HypothesisDeprecationWarning):
        check_can_generate_examples(nps.basic_indices((3, 3, 3), max_dims=4))


def test_basic_indices_default_max_dims_does_not_warn():
    with catch_warnings(record=True) as record:
        check_can_generate_examples(nps.basic_indices((3, 3, 3)))
        check_can_generate_examples(nps.basic_indices((3, 3, 3), allow_newaxis=True))
        assert len(record) == 0
