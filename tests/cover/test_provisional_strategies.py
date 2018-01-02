# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

from __future__ import division, print_function, absolute_import

from binascii import unhexlify

from hypothesis import given
from hypothesis.provisional import emails, ip4_addr_strings, \
    ip6_addr_strings


@given(emails())
def test_is_valid_email(address):
    local, at_, domain = address.rpartition('@')
    assert at_ == '@'
    assert local
    assert domain


@given(ip4_addr_strings())
def test_is_IP4_addr(address):
    as_num = [int(n) for n in address.split('.')]
    assert len(as_num) == 4
    assert all(0 <= n <= 255 for n in as_num)


@given(ip6_addr_strings())
def test_is_IP6_addr(address):
    # Works for non-normalised addresses produced by this strategy, but not
    # a particularly general test
    assert address == address.upper()
    as_hex = address.split(':')
    assert len(as_hex) == 8
    assert all(len(part) == 4 for part in as_hex)
    raw = unhexlify(address.replace(u':', u'').encode('ascii'))
    assert len(raw) == 16
