# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis import given
from tests.common import settings as small_settings
from hypothesis.strategies import text, lists, tuples
from hypothesis.database.backend import SQLiteBackend


@given(lists(tuples(text(), text())), settings=small_settings)
def test_backend_returns_what_you_put_in(xs):
    backend = SQLiteBackend(':memory:')
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
    backend = SQLiteBackend(':memory:')
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

    assert backend.fetch('a') == []


def test_can_double_close():
    backend = SQLiteBackend(':memory:')
    backend.create_db_if_needed()
    backend.close()
    backend.close()


def test_can_delete_keys():
    backend = SQLiteBackend(':memory:')
    backend.save('foo', 'bar')
    backend.save('foo', 'baz')
    backend.delete('foo', 'bar')
    assert list(backend.fetch('foo')) == ['baz']
