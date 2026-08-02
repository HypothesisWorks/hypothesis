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

from hypothesis.strategies import lists

from tests.common import standard_types
from tests.common.debug import check_can_generate_examples


@pytest.mark.parametrize("spec", standard_types, ids=repr)
def test_single_example(spec):
    check_can_generate_examples(spec)


@pytest.mark.parametrize("spec", standard_types, ids=repr)
def test_list_example(spec):
    check_can_generate_examples(lists(spec))
