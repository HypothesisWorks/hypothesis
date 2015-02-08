# coding=utf-8

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function, unicode_literals, division

# END HEADER

import time
from hypothesis.verifier import (
    Verifier, Unfalsifiable, UnsatisfiedAssumption, Flaky
)
from hypothesis.internal.utils.reflection import arg_string
from hypothesis.reporting import current_reporter


def given(*generator_arguments, **kwargs):
    if 'verifier' in kwargs:
        verifier = kwargs.pop('verifier')
        verifier.start_time = time.time()
    elif 'verifier_settings' in kwargs:
        verifier = Verifier(settings=kwargs.pop('verifier_settings'))
    else:
        verifier = Verifier()

    def run_test_with_generator(test):
        def wrapped_test(*arguments):
            # The only thing we accept in falsifying the test are exceptions
            # Returning successfully is always a pass.
            def to_falsify(xs):
                testargs, testkwargs = xs
                try:
                    test(*(arguments + testargs), **testkwargs)
                    return True
                except UnsatisfiedAssumption as e:
                    raise e
                except Exception:  # pylint: disable=broad-except
                    return False

            to_falsify.__name__ = test.__name__
            to_falsify.__qualname__ = getattr(
                test, '__qualname__', test.__name__)

            try:
                falsifying_example = verifier.falsify(
                    to_falsify, (generator_arguments, kwargs))[0]
            except Unfalsifiable:
                return

            current_reporter()(
                'Falsifying example: %s' % (
                    arg_string(
                        test,
                        arguments + falsifying_example[0],
                        falsifying_example[1]
                    )
                )
            )

            # We run this one final time so we get good errors
            # Otherwise we would have swallowed all the reports of it actually
            # having gone wrong.
            test(*(arguments + falsifying_example[0]), **falsifying_example[1])

            # If we get here then something has gone wrong: We found a counter
            # example but it didn't fail when we invoked it again.
            raise Flaky(test, falsifying_example)
        wrapped_test.__name__ = test.__name__
        wrapped_test.__doc__ = test.__doc__
        wrapped_test.verifier = verifier
        return wrapped_test
    return run_test_with_generator
