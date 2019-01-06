# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

import re
import string
from binascii import unhexlify

from hypothesis import given
from hypothesis.provisional import ip4_addr_strings, ip6_addr_strings, urls


@given(urls())
def test_is_URL(url):
    allowed_chars = set(string.ascii_letters + string.digits + "$-_.+!*'(),%/")
    url_schemeless = url.split("://", maxsplit=1)[1]
    path = url_schemeless.split("/", maxsplit=1)[1] if "/" in url_schemeless else ""
    assert all(c in allowed_chars for c in path)
    assert all(
        re.match("^[0-9A-Fa-f]{2}", after_perc) for after_perc in path.split("%")[1:]
    )


@given(ip4_addr_strings())
def test_is_IP4_addr(address):
    as_num = [int(n) for n in address.split(".")]
    assert len(as_num) == 4
    assert all(0 <= n <= 255 for n in as_num)


@given(ip6_addr_strings())
def test_is_IP6_addr(address):
    # Works for non-normalised addresses produced by this strategy, but not
    # a particularly general test
    assert address == address.upper()
    as_hex = address.split(":")
    assert len(as_hex) == 8
    assert all(len(part) == 4 for part in as_hex)
    raw = unhexlify(address.replace(u":", u"").encode("ascii"))
    assert len(raw) == 16
