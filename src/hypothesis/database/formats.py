# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""This is the module responsible for handling conversion of data to and from a
serialized format.

Before you get here, you must convert your objects into *basic data*. Basic
data is any of the following:

    1. A bool, None, an int that fits into 64 bits, or a unicode string
    2. A list of basic data

"""


from __future__ import division, print_function, absolute_import

import json
from abc import abstractmethod

from hypothesis.internal.compat import text_type


class Format(object):

    """A format describes a conversion between basic data and some other type.

    The type can be any thing you like, but the most likely use cases
    are text or binary encodings.

    """

    def __repr__(self):
        return u'%s()' % (self.__class__.__name__,)

    @abstractmethod  # pragma: no cover
    def data_type(self):
        """The type of data that this format will serialize to."""

    @abstractmethod  # pragma: no cover
    def serialize_basic(self, value):
        """Take a basic value and convert it to data_type."""

    @abstractmethod  # pragma: no cover
    def deserialize_data(self, data):
        """Take something of type data_type and convert it back to a basic
        value."""


class JSONFormat(Format):

    """A format that uses the natural encoding to Python's slightly extended
    JSON+ arbitrary precision integers."""

    def data_type(self):
        return text_type

    def serialize_basic(self, value):
        return json.dumps(value)

    def deserialize_data(self, data):
        return json.loads(data)
