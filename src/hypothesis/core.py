# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""This module provides the core primitives of Hypothesis, assume and given."""

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import time
import inspect
from collections import namedtuple

from hypothesis.reporting import current_reporter
from hypothesis.specifiers import just
from hypothesis.searchstrategy import strategy
from hypothesis.internal.verifier import Flaky, Verifier, Unfalsifiable, \
    UnsatisfiedAssumption
from hypothesis.internal.reflection import arg_string, copy_argspec
from hypothesis.utils.dynamicvariables import DynamicVariable

HypothesisProvided = namedtuple('HypothesisProvided', ('value,'))


def assume(condition):
    """Assert a precondition for this test.

    If this is not truthy then the test will abort but not fail and
    Hypothesis will make a "best effort" attempt to avoid similar
    examples in future.

    """
    if not condition:
        raise UnsatisfiedAssumption()
    return True


_debugging_return_failing_example = DynamicVariable(False)


def given(*generator_arguments, **generator_kwargs):
    """A decorator for turning a test function that accepts arguments into a
    randomized test.

    This is the main entry point to Hypothesis. See the full tutorial
    for details of its behaviour.

    """
    if 'verifier' in generator_kwargs:
        verifier = generator_kwargs.pop('verifier')
        verifier.start_time = time.time()
    else:
        verifier = Verifier(
            settings=generator_kwargs.pop('settings', None),
            random=generator_kwargs.pop('random', None),
        )

    if not (generator_arguments or generator_kwargs):
        raise TypeError('given must be called with at least one argument')

    def run_test_with_generator(test):
        original_argspec = inspect.getargspec(test)
        if original_argspec.varargs:
            raise TypeError(
                'varargs are not supported with @given'
            )
        extra_kwargs = [
            k for k in generator_kwargs if k not in original_argspec.args]
        if extra_kwargs and not original_argspec.keywords:
            raise TypeError('%s() got an unexpected keyword argument %r' % (
                extra_kwargs[0]
            ))
        if (
            len(generator_arguments) > len(original_argspec.args)
        ):
            raise TypeError((
                'Too many positional arguments for %s() (got %d but'
                ' expected at most %d') % (
                    test.__name__, len(generator_arguments),
                    len(original_argspec.args)))
        arguments = original_argspec.args + sorted(extra_kwargs)
        specifiers = list(generator_arguments)
        for a in arguments:
            if a in generator_kwargs:
                specifiers.append(generator_kwargs[a])

        argspec = inspect.ArgSpec(
            args=arguments,
            keywords=original_argspec.keywords,
            varargs=original_argspec.varargs,
            defaults=tuple(map(HypothesisProvided, specifiers))
        )

        @copy_argspec(
            test.__name__, argspec
        )
        def wrapped_test(*arguments, **kwargs):
            selfy = None
            # Because we converted all kwargs to given into real args and
            # error if we have neither args nor kwargs, this should always
            # be valid
            assert argspec.args
            selfy = kwargs.get(argspec.args[0])
            if isinstance(selfy, HypothesisProvided):
                selfy = None
            if selfy is not None:
                setup_example = getattr(selfy, 'setup_example', None)
                teardown_example = getattr(selfy, 'teardown_example', None)
            else:
                setup_example = None
                teardown_example = None

            if not any(
                isinstance(x, HypothesisProvided)
                for xs in (arguments, kwargs.values())
                for x in xs
            ):
                # All arguments have been satisfied without needing to invoke
                # hypothesis
                if setup_example is not None:
                    setup_example()
                try:
                    test(*arguments, **kwargs)
                finally:
                    if teardown_example is not None:
                        teardown_example((arguments, kwargs))
                return

            def convert_to_specifier(v):
                if isinstance(v, HypothesisProvided):
                    return v.value
                else:
                    return just(v)

            given_specifier = (
                tuple(map(convert_to_specifier, arguments)),
                {k: convert_to_specifier(v) for k, v in kwargs.items()}
            )

            def to_falsify(xs):
                testargs, testkwargs = xs
                try:
                    test(*testargs, **testkwargs)
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
                    to_falsify, given_specifier,
                    setup_example=setup_example,
                    teardown_example=teardown_example,
                )[0]
            except Unfalsifiable:
                return

            strat = strategy(given_specifier)

            if setup_example is not None:
                setup_example()

            try:
                reified = strat.reify(falsifying_example)
                if _debugging_return_failing_example.value:
                    return reified
                false_args, false_kwargs = reified
                current_reporter()(
                    'Falsifying example: %s(%s)' % (
                        test.__name__,
                        arg_string(
                            test,
                            false_args,
                            false_kwargs,
                        )
                    )
                )
                # We run this one final time so we get good errors
                # Otherwise we would have swallowed all the reports of it
                # actually having gone wrong.
                test(*false_args, **false_kwargs)

            finally:
                if teardown_example is not None:
                    teardown_example(reified)

            # If we get here then something has gone wrong: We found a counter
            # example but it didn't fail when we invoked it again.
            raise Flaky(test, falsifying_example)
        wrapped_test.__name__ = test.__name__
        wrapped_test.__doc__ = test.__doc__
        wrapped_test.verifier = verifier
        wrapped_test.is_hypothesis_test = True
        return wrapped_test
    return run_test_with_generator
