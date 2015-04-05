# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from hypothesis.internal.verifier import Verifier
import hypothesis.settings as hs
from hypothesis.internal.debug import timeout


settings = hs.Settings(max_examples=100, timeout=4)

small_verifier = Verifier(
    settings=settings,
)


__all__ = ['small_verifier', 'timeout']
