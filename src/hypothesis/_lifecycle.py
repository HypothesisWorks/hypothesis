# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2016 David R. MacIver
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

from hypothesis.errors import InvalidDefinition


def lifecycle_executor(lifecycle):
    def execute(data, function):
        try:
            lifecycle.setup_example()
            result = function(data)
            return lifecycle.execute_example_output(result)
        finally:
            lifecycle.teardown_example()
    return execute


def lifecycle_for(value):
    try:
        result = value.hypothesis_lifecycle_definition()
        if not isinstance(result, LifeCycle):
            raise InvalidDefinition(
                'hypothesis_lifecycle_definition returned non-Lifecycle '
                'object %r of type %s' % (result, type(result).__name__))
        validate_lifecycle(result)
        return result
    except AttributeError:
        return None


class LifeCycle(object):
    def setup_example(self):
        pass

    def teardown_example(self):
        pass

    def execute_example_output(self, output):
        return output


def validate_lifecycle(value):
    good_names = set(dir(LifeCycle))

    bad_names = [
        k for k in dir(value)
        if not k.startswith('_')
        and k not in good_names
    ]

    if not bad_names:
        return

    raise InvalidDefinition((
        'Lifecycle object has invalid public name%s: %s. '
        'The public namespace of lifecyle objects is reserved for Hypothesis. '
        'Any names you add to it should be prefixed with an underscore.'
    ) % (
        's' if len(bad_names) > 1 else '',
        ', '.join(bad_names),
    ))
