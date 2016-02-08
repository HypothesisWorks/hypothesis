# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import base64

from hypothesis import given, settings
from hypothesis.database import SQLiteExampleDatabase
from hypothesis.strategies import lists, binary, tuples
from hypothesis.internal.compat import PY26, hrange

small_settings = settings(max_examples=100, timeout=4)

if PY26:
    # Workaround for bug with embedded null characters in a text string under
    # python 2.6
    alphabet = [chr(i) for i in hrange(1, 128)]
else:
    alphabet = None


@given(lists(tuples(binary(), binary())))
@small_settings
def test_backend_returns_what_you_put_in(xs):
    backend = SQLiteExampleDatabase(':memory:')
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
    backend = SQLiteExampleDatabase(':memory:')
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

    assert list(backend.fetch(b'a')) == []


def test_can_double_close():
    backend = SQLiteExampleDatabase(':memory:')
    backend.create_db_if_needed()
    backend.close()
    backend.close()


def test_can_delete_keys():
    backend = SQLiteExampleDatabase(':memory:')
    backend.save(b'foo', b'bar')
    backend.save(b'foo', b'baz')
    backend.delete(b'foo', b'bar')
    assert list(backend.fetch(b'foo')) == [b'baz']


def test_can_fetch_all_keys():
    backend = SQLiteExampleDatabase(':memory:')
    backend.save(b'foo', b'bar')
    backend.save(b'foo', b'baz')
    backend.save(b'boib', b'baz')
    assert len(list(backend.keys())) == 2


def test_ignores_badly_stored_values():
    backend = SQLiteExampleDatabase(':memory:')
    backend.create_db_if_needed()
    with backend.cursor() as cursor:
        cursor.execute("""
            insert into hypothesis_data_mapping(key, value)
            values(?, ?)
        """, (base64.b64encode(b'foo'), u'kittens'))
    assert list(backend.fetch(b'foo')) == []


def test_ignores_badly_stored_keys():
    backend = SQLiteExampleDatabase(':memory:')
    backend.create_db_if_needed()
    with backend.cursor() as cursor:
        cursor.execute("""
            insert into hypothesis_data_mapping(key, value)
            values(?, ?)
        """, (u'badgers', base64.b64encode(b'kittens')))
    assert list(backend.keys()) == []
