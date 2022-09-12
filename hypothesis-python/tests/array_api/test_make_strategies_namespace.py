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

from hypothesis.errors import InvalidArgument
from hypothesis.extra.array_api import make_strategies_namespace, mock_xp


@pytest.mark.parametrize("api_version", [None, "latest", "1970.01", 42])
def test_raise_invalid_argument(api_version):
    with pytest.raises(InvalidArgument):
        make_strategies_namespace(mock_xp, api_version=api_version)
