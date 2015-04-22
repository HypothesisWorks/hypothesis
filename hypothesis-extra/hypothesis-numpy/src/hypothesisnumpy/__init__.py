# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis import strategy
import numpy as np

from hypothesis.internal.compat import binary_type, text_type
from hypothesis.specifiers import integers_in_range


@strategy.extend(np.dtype)
def dtype_strategy(dtype, settings):
    if dtype.kind == 'b':
        result = bool
    elif dtype.kind == 'f':
        result = float
    elif dtype.kind == 'c':
        result = complex
    elif dtype.kind in ('S', 'a', 'V'):
        result = binary_type
    elif dtype.kind == 'u':
        result = integers_in_range(0, 1 << (4 * dtype.itemsize) - 1)
    elif dtype.kind == 'i':
        min_integer = -1 << (4 * dtype.itemsize - 1)
        result = integers_in_range(min_integer, -min_integer - 1)
    elif dtype.kind == 'U':
        result = text_type
    else:
        raise NotImplementedError(
            'No strategy implementation for %r' % (dtype,)
        )
    return strategy(result, settings).map(dtype.type)


def load():
    import hypothesis.extra.numpy as _
    [_]
