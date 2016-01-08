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

import functools

from hypothesis.strategies import none
from hypothesis.settings import Settings
from hypothesis.internal.reflection import get_pretty_function_description
from hypothesis.internal.strategymethod import strategy
from hypothesis.searchstrategy.morphers import MorpherStrategy
from hypothesis.searchstrategy.strategies import MappedSearchStrategy
from hypothesis.searchstrategy.collections import TupleStrategy


class FlatMapStrategy(MappedSearchStrategy):

    def __init__(
        self, strategy, expand
    ):
        super(FlatMapStrategy, self).__init__(
            strategy=TupleStrategy((
                strategy, MorpherStrategy()), tuple))
        self.flatmapped_strategy = strategy
        self.expand = expand
        self.settings = Settings.default

    def __repr__(self):
        if not hasattr(self, u'_cached_repr'):
            self._cached_repr = u'%r.flatmap(%s)' % (
                self.flatmapped_strategy, get_pretty_function_description(
                    self.expand))
        return self._cached_repr

    def pack(self, source_and_morpher):
        source, morpher = source_and_morpher
        return morpher.become(strategy(self.expand(source)))




fail = none().filter(lambda _: False)


def _FromGeneratorPump(initiator, prefix=(None,)):
  it = initiator()
  for p in prefix:
    try:
      last = it.send(p)
    except StopIteration:
      return fail
  if isinstance(last, st.SearchStrategy):
    return last.flatmap(lambda x: _FromGeneratorPump(initiator, prefix+(x,)))
  else:
    return st.just(last)

def FromGenerator(fn):
  @functools.wraps(fn)
  def Replacement(*args):
    return _FromGeneratorPump(functools.partial(fn, *args))
  return Replacement

