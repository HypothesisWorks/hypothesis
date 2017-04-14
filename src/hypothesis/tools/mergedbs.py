#!/usr/bin/env python

# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

"""This is a git merge driver for merging two Hypothesis database files. It
allows you to check in your Hypothesis database into your git repo and have
merging examples work correctly.

You can either install Hypothesis and invoke this as a module, or just copy
this file somewhere convenient and run it directly (it has no dependencies on
the rest of Hypothesis).

You can then set this up by following the instructions in
http://git-scm.com/docs/gitattributes to use this as the merge driver for
wherever you have put your hypothesis database (it is in
.hypothesis/examples.db by default). For example, the following should work
with a default configuration:

In .gitattributes add:

.hypothesis/examples.db merge=hypothesisdb

And in .git/config add:

[merge "hypothesisdb"]
    name = Hypothesis database files
    driver = python -m hypothesis.tools.mergedbs %O %A %B

"""


from __future__ import division, print_function, absolute_import

import sys
import sqlite3
from collections import namedtuple


def get_rows(cursor):
    cursor.execute("""
        select key, value
        from hypothesis_data_mapping
    """)
    for r in cursor:
        yield tuple(r)


Report = namedtuple(u'Report', (u'inserts', u'deletes'))


def merge_paths(ancestor, current, other):
    ancestor = sqlite3.connect(ancestor)
    current = sqlite3.connect(current)
    other = sqlite3.connect(other)
    result = merge_dbs(ancestor, current, other)
    ancestor.close()
    current.close()
    other.close()
    return result


def contains(db, key, value):
    cursor = db.cursor()
    cursor.execute("""
        select 1 from hypothesis_data_mapping
        where key = ? and value = ?
    """, (key, value))
    result = bool(list(cursor))
    cursor.close()
    return result


def merge_dbs(ancestor, current, other):
    other_cursor = other.cursor()
    other_cursor.execute("""
        select key, value
        from hypothesis_data_mapping
    """)
    current_cursor = current.cursor()
    inserts = 0
    for r in other_cursor:
        if not contains(ancestor, *r):
            try:
                current_cursor.execute("""
                    insert into hypothesis_data_mapping(key, value)
                    values(?, ?)
                """, tuple(r))
                inserts += 1
            except sqlite3.IntegrityError:
                pass
            current.commit()
    deletes = 0
    ancestor_cursor = ancestor.cursor()
    ancestor_cursor.execute("""
        select key, value
        from hypothesis_data_mapping
    """)
    for r in ancestor_cursor:
        if not contains(other, *r) and contains(current, *r):
            try:
                current_cursor.execute("""
                    delete from hypothesis_data_mapping
                    where key = ? and value = ?
                """, tuple(r))
                deletes += 1
                current.commit()
            except sqlite3.IntegrityError:
                pass

    return Report(inserts, deletes)


def main():
    _, _, current, other = sys.argv
    result = merge_dbs(destination=current, source=other)
    print(u'%d new entries and %d deletions from merge' % (
        result.inserts, result.deletions))


if __name__ == u'__main__':
    main()
