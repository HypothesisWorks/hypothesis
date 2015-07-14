# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from random import Random

from hypothesis.strategies import sets, integers


def test_template_equality():
    s = sets(integers())
    t = s.draw_and_produce(Random(1))
    assert t != 1

    t2 = s.draw_and_produce(Random(1))
    assert t is not t2
    assert t == t2
    s.reify(t2)
    assert t == t2
    assert hash(t) == hash(t2)

    t3 = s.draw_and_produce(Random(1))
    s.reify(t3)
    for ts in s.full_simplify(Random(1), t3):
        assert t3 != ts


def test_simplifying_unreified_template_does_not_error():
    s = sets(integers())
    t = s.draw_and_produce(Random(1))
    list(s.full_simplify(Random(1), t))


def test_reified_templates_are_simpler():
    s = sets(integers())

    t1 = s.draw_and_produce(Random(1))
    t2 = s.draw_and_produce(Random(1))

    assert t1 == t2
    assert not s.strictly_simpler(t1, t2)

    s.reify(t1)
    print(t1, t2)
    assert s.strictly_simpler(t1, t2)
    assert not s.strictly_simpler(t2, t1)
