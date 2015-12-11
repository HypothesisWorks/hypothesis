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

from hypothesis import Settings
from hypothesis.internal.compat import hrange, getargspec, \
    unicode_safe_repr
from hypothesis.internal.reflection import arg_string, \
    convert_keyword_arguments, convert_positional_arguments
from hypothesis.searchstrategy.strategies import SearchStrategy


class reprmangledtuple(tuple):

    def __repr__(self):
        try:
            return super(reprmangledtuple, self).__repr__()
        except UnicodeEncodeError:  # pragma: no cover
            if len(self) == 1:
                return u"(%s,)" % (unicode_safe_repr(self[0]),)
            else:
                return u"(%s)" % (u", ".join(
                    map(unicode_safe_repr, self)
                ))


def tupleize(x):
    if isinstance(x, (tuple, list)):
        return reprmangledtuple(x)
    else:
        return x


class DeferredStrategy(SearchStrategy):

    """A strategy which is defined purely by conversion to and from another
    strategy.

    Its parameter and distribution come from that other strategy.

    """

    def __init__(self, function, args, kwargs):
        SearchStrategy.__init__(self)
        self.__wrapped_strategy = None
        self.__representation = None
        self.__function = function
        self.__args = tuple(map(tupleize, args))
        self.__kwargs = dict(
            (k, tupleize(v)) for k, v in kwargs.items()
        )
        self.__settings = Settings.default or Settings()

    @property
    def wrapped_strategy(self):
        if self.__wrapped_strategy is None:
            with self.__settings:
                self.__wrapped_strategy = self.__function(
                    *self.__args,
                    **self.__kwargs
                )
        return self.__wrapped_strategy

    def validate(self):
        self.wrapped_strategy.validate()

    @property
    def template_upper_bound(self):
        return self.wrapped_strategy.template_upper_bound

    def __repr__(self):
        if self.__representation is None:
            _args = self.__args
            _kwargs = self.__kwargs
            argspec = getargspec(self.__function)
            defaults = {}
            if argspec.defaults is not None:
                for k in hrange(1, len(argspec.defaults) + 1):
                    defaults[argspec.args[-k]] = argspec.defaults[-k]
            if len(argspec.args) > 1 or argspec.defaults:
                _args, _kwargs = convert_positional_arguments(
                    self.__function, _args, _kwargs)
            else:
                _args, _kwargs = convert_keyword_arguments(
                    self.__function, _args, _kwargs)
            kwargs_for_repr = dict(_kwargs)
            for k, v in defaults.items():
                if k in kwargs_for_repr and kwargs_for_repr[k] is defaults[k]:
                    del kwargs_for_repr[k]
            self.__representation = u'%s(%s)' % (
                self.__function.__name__,
                arg_string(
                    self.__function, _args, kwargs_for_repr, reorder=False),
            )
        return self.__representation

    def draw_parameter(self, random):
        return self.wrapped_strategy.draw_parameter(random)

    def draw_template(self, random, pv):
        return self.wrapped_strategy.draw_template(random, pv)

    def reify(self, value):
        return self.wrapped_strategy.reify(value)

    def simplifiers(self, random, template):
        return self.wrapped_strategy.simplifiers(random, template)

    def strictly_simpler(self, x, y):
        return self.wrapped_strategy.strictly_simpler(x, y)

    def to_basic(self, template):
        return self.wrapped_strategy.to_basic(template)

    def from_basic(self, data):
        return self.wrapped_strategy.from_basic(data)
