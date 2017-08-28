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
import gzip
import pickle
import tempfile
import unicodedata

from hypothesis.configuration import tmpdir, storage_directory
from hypothesis.internal.compat import hunichr


def charmap_file():
    return os.path.join(
        storage_directory('unicodedata', unicodedata.unidata_version),
        'charmap.pickle.gz'
    )


_charmap = None


def charmap():
    """Return a dict that maps a Unicode category, to a tuple of 2-tuples
    covering the codepoint intervals for characters in that category.

    >>> charmap()['Co']
    ((57344, 63743), (983040, 1048573), (1048576, 1114109))

    """
    global _charmap
    # Best-effort caching in the face of missing files and/or unwritable
    # filesystems is fairly simple: check if loaded, else try loading,
    # else calculate and try writing the cache.
    if _charmap is None:
        f = charmap_file()
        try:
            with gzip.GzipFile(f, 'rb') as i:
                _charmap = dict(pickle.load(i))

        except Exception:
            tmp_charmap = {}
            for i in range(0, sys.maxunicode + 1):
                cat = unicodedata.category(hunichr(i))
                rs = tmp_charmap.setdefault(cat, [])
                if rs and rs[-1][-1] == i - 1:
                    rs[-1][-1] += 1
                else:
                    rs.append([i, i])
            _charmap = {k: tuple((map(tuple, v)))
                        for k, v in tmp_charmap.items()}

            try:
                # Write the Unicode table atomically
                fd, tmpfile = tempfile.mkstemp(dir=tmpdir())
                os.close(fd)
                # Explicitly set the mtime to get reproducible output
                with gzip.GzipFile(tmpfile, 'wb', mtime=1) as o:
                    pickle.dump(sorted(_charmap.items()), o,
                                pickle.HIGHEST_PROTOCOL)
                os.rename(tmpfile, f)
            except Exception:  # pragma: no cover
                pass
    assert _charmap is not None
    return _charmap


_categories = None


def categories():
    """Return a list of Unicode categories in a normalised order.

    >>> categories() # doctest: +ELLIPSIS
    ['Zl', 'Zp', 'Co', 'Me', 'Pc', ..., 'Cc', 'Cs']

    """
    global _categories
    if _categories is None:
        cm = charmap()
        _categories = sorted(
            cm.keys(), key=lambda c: len(cm[c])
        )
        _categories.remove('Cc')  # Other, Control
        _categories.remove('Cs')  # Other, Surrogate
        _categories.append('Cc')
        _categories.append('Cs')
    return _categories


def _union_intervals(x, y):
    """Merge two sequences of intervals into a single tuple of intervals.

    Any integer bounded by `x` or `y` is also bounded by the result.

    >>> _union_intervals([(3, 10)], [(1, 2), (5, 17)])
    ((1, 17),)

    """
    if not x:
        return tuple((u, v) for u, v in y)
    if not y:
        return tuple((u, v) for u, v in x)
    intervals = sorted(x + y, reverse=True)
    result = [intervals.pop()]
    while intervals:
        # 1. intervals is in descending order
        # 2. pop() takes from the RHS.
        # 3. (a, b) was popped 1st, then (u, v) was popped 2nd
        # 4. Therefore: a <= u
        # 5. We assume that u <= v and a <= b
        # 6. So we need to handle 2 cases of overlap, and one disjoint case
        #    |   u--v     |   u----v   |       u--v  |
        #    |   a----b   |   a--b     |  a--b       |
        u, v = intervals.pop()
        a, b = result[-1]
        if u <= b + 1:
            # Overlap cases
            result[-1] = (a, max(v, b))
        else:
            # Disjoint case
            result.append((u, v))
    return tuple(result)


def _intervals(s):
    """Return a tuple of intervals, covering the codepoints of characters in
    `s`.

    >>> _intervals('abcdef0123456789')
    ((48, 57), (97, 102))

    """
    intervals = [(ord(c), ord(c)) for c in sorted(s)]
    return _union_intervals(intervals, intervals)


category_index_cache = {
    (): (),
}


def _category_key(exclude, include):
    """Return a normalised tuple of all Unicode categories that are in
    `include`, but not in `exclude`.

    If include is None then default to including all categories.
    Any item in include that is not a unicode character will be excluded.

    >>> _category_key(exclude=['So'], include=['Lu', 'Me', 'Cs', 'So', 'Xx'])
    ('Me', 'Lu', 'Cs')

    """
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
    """Return a tuple of codepoint intervals covering characters that match one
    or more categories in the tuple of categories `key`.

    >>> all_categories = tuple(categories())
    >>> _query_for_key(all_categories)
    ((0, 1114111),)
    >>> _query_for_key(('Zl', 'Zp', 'Co'))
    ((8232, 8233), (57344, 63743), (983040, 1048573), (1048576, 1114109))

    """
    try:
        return category_index_cache[key]
    except KeyError:
        pass
    assert key
    cs = categories()
    if len(key) == len(cs):
        result = ((0, sys.maxunicode),)
    else:
        result = _union_intervals(
            _query_for_key(key[:-1]), charmap()[key[-1]]
        )
    category_index_cache[key] = result
    return result


limited_category_index_cache = {}


def query(
    exclude_categories=(), include_categories=None,
    min_codepoint=None,
    max_codepoint=None,
    include_characters=''
):
    """Return a tuple of intervals covering the codepoints for all characters
    that meet the critera (min_codepoint <= codepoint(c) <= max_codepoint and
    any(cat in include_categories for cat in categories(c)) and all(cat not in
    exclude_categories for cat in categories(c)) or (c in include_characters)

    >>> query()
    ((0, 1114111),)
    >>> query(min_codepoint=0, max_codepoint=128)
    ((0, 128),)
    >>> query(min_codepoint=0, max_codepoint=128, include_categories=['Lu'])
    ((65, 90),)
    >>> query(min_codepoint=0, max_codepoint=128, include_categories=['Lu'],
    ...       include_characters=u'☃')
    ((65, 90), (9731, 9731))

    """
    if min_codepoint is None:
        min_codepoint = 0
    if max_codepoint is None:
        max_codepoint = sys.maxunicode
    catkey = _category_key(exclude_categories, include_categories)
    character_intervals = _intervals(include_characters or '')
    qkey = (catkey, min_codepoint, max_codepoint, character_intervals)
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
    result = _union_intervals(result, character_intervals)
    limited_category_index_cache[qkey] = result
    return result
