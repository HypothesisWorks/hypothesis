from __future__ import print_function, unicode_literals
import time
from hypothesis.verifier import (
    Verifier, Unfalsifiable, UnsatisfiedAssumption, Flaky
)
from hypothesis.internal.utils.reflection import convert_positional_arguments


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

            cargs, ckwargs = convert_positional_arguments(
                test,
                arguments + falsifying_example[0],
                falsifying_example[1],
            )

            print(
                "Falsifying example: %s" % ', '.join(
                    [repr(x) for x in cargs] +
                    sorted(
                        ["%s=%s" % (k, repr(v)) for k, v in ckwargs.items()])
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
        return wrapped_test
    return run_test_with_generator
