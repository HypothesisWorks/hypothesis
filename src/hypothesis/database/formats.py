# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, unicode_literals

import json
from abc import abstractmethod

from hypothesis.internal.compat import text_type


class Format(object):

    """A format describes a conversion between basic data (see
    hypothesis.database.converter) and some other type.

    The type can be any thing you like, but the most likely use cases
    are text or binary encodings.

    """

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
