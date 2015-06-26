#!/usr/bin/env python

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


from __future__ import division, print_function, absolute_import, \
    unicode_literals

import sys
import sqlite3


def get_rows(cursor):
    cursor.execute("""
        select key, value
        from hypothesis_data_mapping
    """)
    for r in cursor:
        yield tuple(r)


def merge_dbs(source, destination):
    destination = sqlite3.connect(destination)
    source = sqlite3.connect(source)
    source_cursor = source.cursor()
    source_cursor.execute("""
        select key, value
        from hypothesis_data_mapping
    """)
    destination_cursor = destination.cursor()
    successes = 0
    for r in source_cursor:
        try:
            destination_cursor.execute("""
                insert into hypothesis_data_mapping(key, value)
                values(?, ?)
            """, tuple(r))
            successes += 1
        except sqlite3.IntegrityError:
            pass
        destination.commit()
    print('%d new entries from merge' % (successes,))


def main():
    _, _, current, other = sys.argv
    merge_dbs(destination=current, source=other)

if __name__ == '__main__':
    main()
