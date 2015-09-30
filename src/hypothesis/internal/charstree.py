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

import os
import sys
import zlib
import bisect
import functools
import itertools
import unicodedata

import marshal
from hypothesis.errors import InvalidArgument
from hypothesis.settings import hypothesis_home_dir
from hypothesis.internal.compat import hrange, hunichr

__all__ = (
    'ascii_tree',
    'unicode_tree',
    'categories',
    'category_by_codepoint',
    'codepoints',
    'codepoints_for_category',
    'filter_tree',
    'random_codepoint',
)


ASCII_TREE = {}
UNICODE_TREE = {}


def ascii_tree():
    """Returns tree for ASCII characters."""
    global ASCII_TREE
    if not ASCII_TREE:
        ASCII_TREE = filter_tree(unicode_tree(), max_codepoint=127)
    return ASCII_TREE


def unicode_tree():
    """Returns tree of Unicode characters."""
    global UNICODE_TREE
    if not UNICODE_TREE:
        try:
            UNICODE_TREE = load_tree()
        except:
            UNICODE_TREE = make_tree()
            try:
                dump_tree(UNICODE_TREE)
            except:  # pragma: no cover
                pass
    return UNICODE_TREE


def categories(tree):
    """Returns list of all categories in specified tree."""
    return list(tree)


def category_by_codepoint(tree, codepoint):
    """Returns category by specified code point in the tree."""
    categories = list(filter_tree(
        tree, min_codepoint=codepoint, max_codepoint=codepoint))
    if not categories:
        return None
    assert len(categories) == 1
    return categories[0]


def codepoints(tree):
    """Iterates over all code points in specified tree.

    Code points get yielded in single stream category by category.

    """
    by_category = functools.partial(codepoints_for_category, tree)
    return itertools.chain.from_iterable(map(by_category, categories(tree)))


def codepoints_for_category(tree, category):
    """Iterates over all code points of the specified category in the tree."""
    for value in iter_values(tree[category]):
        for cp in hrange(value[0], value[1] + 1):
            yield cp


def random_codepoint(tree, category, random):
    """Returns random code point for specified category in the tree."""
    base, values = select_values(
        tree, category, lambda ns: random.choice(list(ns)))
    assert values, 'no values found'
    value = random.choice(values)
    if value[0] == value[1]:
        return base + value[0]
    return random.randint(base + value[0], base + value[1])


def filter_tree(tree, whitelist_categories=None, blacklist_categories=None,
                blacklist_characters=None, min_codepoint=0,
                max_codepoint=sys.maxunicode):
    """Filters tree by Unicode categories and code points range."""
    if whitelist_categories and blacklist_categories:
        raise InvalidArgument('cannot have both white and black list of'
                              ' categories at the same time')

    if min_codepoint > max_codepoint:
        raise InvalidArgument('min code point is greater than max')

    categories = set(tree)
    if whitelist_categories:
        categories &= set(whitelist_categories)
    if blacklist_categories:
        categories -= set(blacklist_categories)
    if not blacklist_characters:
        blacklist_characters = set([])

    return do_filter_tree(tree, categories, blacklist_characters,
                          min_codepoint, max_codepoint)


def do_filter_tree(tree, categories, blacklist_characters,
                   min_codepoint, max_codepoint):
    new_tree = {}
    for key, subtree in tree.items():
        if key not in categories:
            continue

        subtree = do_filter_tree_by_codepoints(
            subtree, min_codepoint, max_codepoint, {}, 0)

        if not subtree:
            continue

        subtree = do_filter_tree_by_characters(
            subtree, sorted(blacklist_characters), {}, 0)

        if not subtree:
            continue

        new_tree[key] = subtree

    return new_tree


def do_filter_tree_by_codepoints(tree, min_codepoint, max_codepoint,
                                 acc, base):
    for key, value in tree.items():
        this_base = base + key

        if this_base > max_codepoint:
            continue

        if isinstance(value, dict):
            subtree = do_filter_tree_by_codepoints(
                value, min_codepoint, max_codepoint, {}, this_base)
            if subtree:
                acc[key] = subtree

        else:
            filtered_items = []

            for item in value:
                if item[0] + this_base > max_codepoint:
                    continue
                if item[1] + this_base < min_codepoint:
                    continue
                if item[0] + this_base < min_codepoint:
                    item = (min_codepoint - this_base, item[1])
                if item[1] + this_base > max_codepoint:
                    item = (item[0], max_codepoint - this_base)
                filtered_items.append(item)

            if filtered_items:
                acc[key] = tuple(filtered_items)

    return acc


def do_filter_tree_by_characters(tree, blacklist_characters, acc, base):
    if not blacklist_characters:
        return tree

    for key, value in tree.items():
        this_base = base + key

        index = bisect.bisect(blacklist_characters, hunichr(this_base))
        characters = blacklist_characters[index - 1 if index else 0:]

        if isinstance(value, dict):
            subtree = do_filter_tree_by_characters(
                value, characters, {}, this_base)
            if subtree:
                acc[key] = subtree
        else:
            filtered_value = value
            for character in characters:
                codepoint = ord(character)
                value_acc = []
                for item in filtered_value:
                    locp, hicp = item[0] + this_base, item[1] + this_base
                    if locp == codepoint == hicp:
                        continue
                    elif not (locp <= codepoint <= hicp):
                        value_acc.append(item)
                    elif locp == codepoint:
                        item = (codepoint + 1 - this_base, item[1])
                        value_acc.append(item)
                    elif hicp == codepoint:
                        item = (item[0], codepoint - 1 - this_base)
                        value_acc.append(item)
                    else:
                        value_acc.append((item[0], codepoint - 1 - this_base))
                        value_acc.append((codepoint + 1 - this_base, item[1]))
                filtered_value = value_acc
            if filtered_value:
                acc[key] = tuple(filtered_value)
    return acc


def select_values(tree, category, selector):
    if category not in tree:
        return 0, []
    base = 0
    namespace = tree[category]
    while True:
        key = selector(namespace)
        namespace = namespace[key]
        base += key
        if isinstance(namespace, dict):
            continue
        return base, namespace


def iter_values(namespace, base=0):
    if isinstance(namespace, dict):
        for key in namespace:
            for value in iter_values(namespace[key], base + key):
                yield value
    else:
        for value in namespace:
            yield (base + value[0], base + value[1])


def make_tree():
    def new_tree():
        tree = {}
        for codepoint in hrange(0, sys.maxunicode + 1):
            cat = unicodedata.category(hunichr(codepoint))
            target = tree.setdefault(cat, [])
            if target and codepoint == target[-1][-1] + 1:
                target[-1][-1] += 1
            else:
                target.append([codepoint, codepoint])
        return tree

    def fold(tree, factor):
        for key, values in tree.items():
            if isinstance(values, dict):
                fold(values, factor)
            else:
                tree[key] = fold_values(values, factor)

    def fold_values(values, factor):
        group = {}
        by_factor = lambda i: i[0] & factor
        for ns, items in itertools.groupby(values, key=by_factor):
            namespace = group.setdefault(ns, [])
            namespace.extend([[i[0] - ns, i[1] - ns] for i in items])
        return group

    tree = new_tree()
    # Multi folding optimizes file size ~10-15% and improves algorithmic cost
    # of code point lookup
    fold(tree, 0xfff000)
    fold(tree, 0xffff00)
    fold(tree, 0xfffff0)
    return tree


def cache_file_path():
    return os.path.join(hypothesis_home_dir(),
                        os.path.basename(__file__) + '.cache')


def dump_tree(tree):  # pragma: no cover
    dump = marshal.dumps(tree, version=2)
    with open(cache_file_path(), 'wb') as f:
        f.write(zlib.compress(dump))


def load_tree():  # pragma: no cover
    with open(cache_file_path(), 'rb') as f:
        dump = zlib.decompress(f.read())
    return marshal.loads(dump)
