# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, unicode_literals

import time
import inspect
from collections import namedtuple

from hypothesis.verifier import Flaky, Verifier, Unfalsifiable, \
    UnsatisfiedAssumption
from hypothesis.reporting import current_reporter
from hypothesis.descriptors import just
from hypothesis.internal.utils.reflection import arg_string, copy_argspec

HypothesisProvided = namedtuple('HypothesisProvided', ('value,'))


def given(*generator_arguments, **generator_kwargs):
    if 'verifier' in generator_kwargs:
        verifier = generator_kwargs.pop('verifier')
        verifier.start_time = time.time()
    elif 'verifier_settings' in generator_kwargs:
        verifier = Verifier(settings=generator_kwargs.pop('verifier_settings'))
    else:
        verifier = Verifier()

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
        descriptors = list(generator_arguments)
        for a in arguments:
            if a in generator_kwargs:
                descriptors.append(generator_kwargs[a])

        argspec = inspect.ArgSpec(
            args=arguments,
            keywords=original_argspec.keywords,
            varargs=original_argspec.varargs,
            defaults=list(map(HypothesisProvided, descriptors))
        )

        @copy_argspec(
            test.__name__, argspec
        )
        def wrapped_test(*arguments, **kwargs):
            if not any(
                isinstance(x, HypothesisProvided)
                for xs in (arguments, kwargs.values())
                for x in xs
            ):
                # All arguments have been satisfied without needing to invoke
                # hypothesis
                test(*arguments, **kwargs)
                return

            def convert_to_descriptor(v):
                if isinstance(v, HypothesisProvided):
                    return v.value
                else:
                    return just(v)

            given_descriptor = (
                tuple(map(convert_to_descriptor, arguments)),
                {k: convert_to_descriptor(v) for k, v in kwargs.items()}
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
                    to_falsify, given_descriptor)[0]
            except Unfalsifiable:
                return

            false_args, false_kwargs = falsifying_example
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
            # Otherwise we would have swallowed all the reports of it actually
            # having gone wrong.
            test(*false_args, **false_kwargs)

            # If we get here then something has gone wrong: We found a counter
            # example but it didn't fail when we invoked it again.
            raise Flaky(test, falsifying_example)
        wrapped_test.__name__ = test.__name__
        wrapped_test.__doc__ = test.__doc__
        wrapped_test.verifier = verifier
        return wrapped_test
    return run_test_with_generator
