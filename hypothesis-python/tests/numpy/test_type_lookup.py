# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import numpy as np
from numpy.typing import NDArray

from hypothesis import strategies as st

from tests.common.debug import assert_all_examples


def test_from_numpy_ndarray_any_type():
    assert_all_examples(st.from_type(NDArray), lambda obj: isinstance(obj, np.ndarray))


def test_from_numpy_ndarray_specific_type():
    def check_dtype(obj):
        return obj.dtype == np.float64

    assert_all_examples(st.from_type(NDArray[np.float64]), check_dtype)
