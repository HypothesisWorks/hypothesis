# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import strategies as st

from tests.common.debug import minimal


def test_large_branching_tree():
    tree = st.deferred(lambda: st.integers() | st.tuples(tree, tree, tree, tree, tree))
    assert minimal(tree) == 0
    assert minimal(tree, lambda x: isinstance(x, tuple)) == (0,) * 5


def test_non_trivial_json():
    json = st.deferred(lambda: st.none() | st.floats() | st.text() | lists | objects)

    lists = st.lists(json)
    objects = st.dictionaries(st.text(), json)

    assert minimal(json) is None
    assert minimal(json, lambda x: isinstance(x, list) and x) == [None]
    assert minimal(
        json, lambda x: isinstance(x, dict) and isinstance(x.get(""), list)
    ) == {"": []}


def test_self_recursive_lists():
    x = st.deferred(lambda: st.lists(x))
    assert minimal(x) == []
    assert minimal(x, bool) == [[]]
    assert minimal(x, lambda x: len(x) > 1) == [[], []]
