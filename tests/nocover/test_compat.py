# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest
from hypothesis.internal.compat import hrange, qualname, BAD_PY3


def test_small_hrange():
    assert list(hrange(5)) == [0, 1, 2, 3, 4]
    assert list(hrange(3, 5)) == [3, 4]
    assert list(hrange(1, 10, 2)) == [1, 3, 5, 7, 9]


def test_large_hrange():
    n = 1 << 1024
    assert list(hrange(n, n + 5, 2)) == [n, n + 2, n + 4]
    assert list(hrange(n, n)) == []

    with pytest.raises(ValueError):
        hrange(n, n, 0)


class Foo():
    def bar(self):
        pass


@pytest.mark.skipif(
    BAD_PY3,
    reason="Python 3.2 and less have a terrible object model."
)
def test_qualname():
    assert qualname(Foo.bar) == "Foo.bar"
    assert qualname(Foo().bar) == "Foo.bar"
    assert qualname(qualname) == "qualname"
