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

from __future__ import division, print_function, absolute_import

import os
import sys
import pickle
import tempfile
import unicodedata

from hypothesis.configuration import tmpdir, storage_directory
from hypothesis.internal.compat import GzipFile, FileExistsError, hunichr


def charmap_file():
    return os.path.join(
        storage_directory('unicodedata', unicodedata.unidata_version),
        'charmap.pickle.gz'
    )


_charmap = None


def charmap():
    global _charmap
    if _charmap is None:
        f = charmap_file()
        if not os.path.exists(f):
            tmp_charmap = {}
            for i in range(0, sys.maxunicode + 1):
                cat = unicodedata.category(hunichr(i))
                rs = tmp_charmap.setdefault(cat, [])
                if rs and rs[-1][-1] == i - 1:
                    rs[-1][-1] += 1
                else:
                    rs.append([i, i])
            # We explicitly set the mtime to an arbitrary value so as to get
            # a stable format for our charmap.
            data = sorted(
                (k, tuple((map(tuple, v))))
                for k, v in tmp_charmap.items())

            # Write the Unicode table atomically
            fd, tmpfile = tempfile.mkstemp(dir=tmpdir())
            os.close(fd)
            with GzipFile(tmpfile, 'wb', mtime=1) as o:
                o.write(pickle.dumps(data, pickle.HIGHEST_PROTOCOL))
            try:
                os.rename(tmpfile, f)
            except FileExistsError:  # pragma: no cover
                # This exception is only raised on Windows, and coverage is
                # measured on Linux.
                pass
        with GzipFile(f, 'rb') as i:
            _charmap = dict(pickle.loads(i.read()))
    assert _charmap is not None
    return _charmap


_categories = None


def categories():
    global _categories
    if _categories is None:
        cm = charmap()
        _categories = sorted(
            cm.keys(), key=lambda c: len(cm[c])
        )
        _categories.remove('Cc')
        _categories.remove('Cs')
        _categories.append('Cc')
        _categories.append('Cs')
    return _categories


def _union_interval_lists(x, y):
    if not x:
        return y
    if not y:
        return x
    intervals = sorted(x + y, reverse=True)
    result = [intervals.pop()]
    while intervals:
        u, v = intervals.pop()
        a, b = result[-1]
        if u <= b + 1:
            result[-1] = (a, v)
        else:
            result.append((u, v))
    return tuple(result)


category_index_cache = {
    (): (),
}


def _category_key(exclude, include):
    cs = categories()
    if include is None:
        include = set(cs)
    else:
        include = set(include)
    exclude = set(exclude or ())
    include -= exclude
    result = tuple(c for c in cs if c in include)
    return result


def _query_for_key(key):
    try:
        return category_index_cache[key]
    except KeyError:
        pass
    assert key
    cs = categories()
    if len(key) == len(cs):
        result = ((0, sys.maxunicode),)
    else:
        result = _union_interval_lists(
            _query_for_key(key[:-1]), charmap()[key[-1]]
        )
    category_index_cache[key] = result
    return result


limited_category_index_cache = {}


def query(
    exclude_categories=(), include_categories=None,
    min_codepoint=None, max_codepoint=None
):
    if min_codepoint is None:
        min_codepoint = 0
    if max_codepoint is None:
        max_codepoint = sys.maxunicode
    catkey = _category_key(exclude_categories, include_categories)
    qkey = (catkey, min_codepoint, max_codepoint)
    try:
        return limited_category_index_cache[qkey]
    except KeyError:
        pass
    base = _query_for_key(catkey)
    result = []
    for u, v in base:
        if v >= min_codepoint and u <= max_codepoint:
            result.append((
                max(u, min_codepoint), min(v, max_codepoint)
            ))
    result = tuple(result)
    limited_category_index_cache[qkey] = result
    return result
