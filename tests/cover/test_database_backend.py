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

from __future__ import division, print_function, absolute_import

from hypothesis import given
from tests.common import settings as small_settings
from hypothesis.strategies import text, lists, tuples
from hypothesis.internal.compat import PY26, hrange
from hypothesis.database.backend import SQLiteBackend

if PY26:
    alphabet = [chr(i) for i in hrange(128)]
else:
    alphabet = None


@given(
    lists(tuples(text(alphabet=alphabet), text(alphabet=alphabet))),
    settings=small_settings)
def test_backend_returns_what_you_put_in(xs):
    backend = SQLiteBackend(u':memory:')
    mapping = {}
    for key, value in xs:
        mapping.setdefault(key, set()).add(value)
        backend.save(key, value)
    for key, values in mapping.items():
        backend_contents = list(backend.fetch(key))
        distinct_backend_contents = set(backend_contents)
        assert len(backend_contents) == len(distinct_backend_contents)
        assert distinct_backend_contents == set(values)


def test_does_not_commit_in_error_state():
    backend = SQLiteBackend(u':memory:')
    backend.create_db_if_needed()
    try:
        with backend.cursor() as cursor:
            cursor.execute("""
                insert into hypothesis_data_mapping(key, value)
                values("a", "b")
            """)
            raise ValueError()
    except ValueError:
        pass

    assert backend.fetch(u'a') == []


def test_can_double_close():
    backend = SQLiteBackend(u':memory:')
    backend.create_db_if_needed()
    backend.close()
    backend.close()


def test_can_delete_keys():
    backend = SQLiteBackend(u':memory:')
    backend.save(u'foo', u'bar')
    backend.save(u'foo', u'baz')
    backend.delete(u'foo', u'bar')
    assert list(backend.fetch(u'foo')) == [u'baz']


def test_can_fetch_all_keys():
    backend = SQLiteBackend(u':memory:')
    backend.save(u'foo', u'bar')
    backend.save(u'foo', u'baz')
    backend.save(u'boib', u'baz')
    assert len(list(backend.keys())) == 2
