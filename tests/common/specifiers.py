# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from collections import namedtuple

from hypothesis.specifiers import one_of, sampled_from
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.searchstrategy.narytree import Leaf, NAryTree
from hypothesis.searchstrategy.strategies import MappedSearchStrategy, \
    strategy

primitive_types = [
    int, float, text_type, binary_type, bool, complex, type(None)]


Descriptor = namedtuple('Descriptor', ('specifier',))


class DescriptorStrategy(MappedSearchStrategy):

    def __init__(self, settings):
        super(DescriptorStrategy, self).__init__(
            strategy=strategy(NAryTree(
                branch_labels=sampled_from((
                    tuple, dict, set, frozenset, list
                )),
                branch_keys=one_of((int, str)),
                leaf_values=sampled_from((
                    int, float, text_type, binary_type,
                    bool, complex, type(None)))
            ), settings)
        )

    def pack(self, value):
        if isinstance(value, Leaf):
            return value.value
        else:
            label = value.label
            if label == dict:
                return {
                    k: self.pack(v)
                    for k, v in value.keyed_children
                }
            else:
                children = [self.pack(v) for k, v in value.keyed_children]
                try:
                    return label(children)
                except TypeError:
                    return tuple(children)


@strategy.extend_static(Descriptor)
def specifier_strategy(cls, settings):
    return DescriptorStrategy(settings)
