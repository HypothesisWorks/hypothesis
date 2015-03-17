# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis.internal.reflection import get_pretty_function_description


class HypothesisException(Exception):

    """Generic parent class for exceptions thrown by Hypothesis."""
    pass


class UnsatisfiedAssumption(HypothesisException):

    """An internal error raised by assume.

    If you're seeing this error something has gone wrong.

    """

    def __init__(self):
        super(UnsatisfiedAssumption, self).__init__('Unsatisfied assumption')


class Unfalsifiable(HypothesisException):

    """The hypothesis we have been asked to falsify appears to be always true.

    This does not guarantee that no counter-example exists, only that we
    were unable to find one.

    """

    def __init__(self, hypothesis, extra=''):
        super(Unfalsifiable, self).__init__(
            'Unable to falsify hypothesis %s%s' % (
                get_pretty_function_description(hypothesis), extra)
        )


class Exhausted(Unfalsifiable):

    """We appear to have considered the entire example space available before
    we ran out of time or number of examples.

    This does not guarantee that we have considered the whole example
    space (it could just be a bad search strategy) but it makes it
    pretty likely that this hypothesis is just always true.

    """

    def __init__(self, hypothesis, n_examples):
        super(Exhausted, self).__init__(
            hypothesis, ' exhausted parameter space after %d examples' % (
                n_examples,
            )
        )


class Unsatisfiable(HypothesisException):

    """We ran out of time or examples before we could find enough examples
    which satisfy the assumptions of this hypothesis.

    This could be because the function is too slow. If so, try upping
    the timeout. It could also be because the function is using assume
    in a way that is too hard to satisfy. If so, try writing a custom
    strategy or using a better starting point (e.g if you are requiring
    a list has unique values you could instead filter out all duplicate
    values from the list)

    """

    def __init__(self, hypothesis, examples, run_time):
        super(Unsatisfiable, self).__init__((
            'Unable to satisfy assumptions of hypothesis %s. ' +
            'Only %s examples found after %g seconds'
        ) % (
            get_pretty_function_description(hypothesis),
            str(examples),
            run_time))


class Flaky(HypothesisException):

    """
    This function appears to fail non-deterministically: We have seen it fail
    when passed this example at least once, but a subsequent invocation did not
    fail.

    Common causes for this problem are:
        1. The function depends on external state. e.g. it uses an external
           random number generator. Try to make a version that passes all the
           relevant state in from Hypothesis.
        2. The function is suffering from too much recursion and its failure
           depends sensitively on where it's been called from.
        3. The function is timing sensitive and can fail or pass depending on
           how long it takes. Try breaking it up into smaller functions which
           dont' do that and testing those instead.
    """

    def __init__(self, hypothesis, example):
        super(Flaky, self).__init__((
            'Hypothesis %r produces unreliable results: %r falsified it on the'
            ' first call but did not on a subsequent one'
        ) % (get_pretty_function_description(hypothesis), example))


class Timeout(Unsatisfiable):

    """We were unable to find enough examples that satisfied the preconditions
    of this hypothesis in the amount of time allotted to us."""


class WrongFormat(HypothesisException, ValueError):

    """An exception indicating you have attempted to serialize a value that
    does not match the type described by this format."""


class BadData(HypothesisException, ValueError):

    """The data that we got out of the database does not seem to match the data
    we could have put into the database given this schema."""
