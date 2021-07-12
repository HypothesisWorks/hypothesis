# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

import os
import sys
import traceback
from inspect import getframeinfo
from pathlib import Path
from typing import Dict

import hypothesis
from hypothesis.errors import (
    DeadlineExceeded,
    Flaky,
    HypothesisException,
    MultipleFailures,
    StopTest,
    UnsatisfiedAssumption,
)


def belongs_to(package):
    if not hasattr(package, "__file__"):  # pragma: no cover
        return lambda filepath: False

    root = Path(package.__file__).resolve().parent
    cache = {str: {}, bytes: {}}

    def accept(filepath):
        ftype = type(filepath)
        try:
            return cache[ftype][filepath]
        except KeyError:
            pass
        try:
            Path(filepath).resolve().relative_to(root)
            result = True
        except Exception:
            result = False
        cache[ftype][filepath] = result
        return result

    accept.__name__ = f"is_{package.__name__}_file"
    return accept


PREVENT_ESCALATION = os.getenv("HYPOTHESIS_DO_NOT_ESCALATE") == "true"

FILE_CACHE: Dict[bytes, bool] = {}


is_hypothesis_file = belongs_to(hypothesis)

HYPOTHESIS_CONTROL_EXCEPTIONS = (DeadlineExceeded, StopTest, UnsatisfiedAssumption)


def escalate_hypothesis_internal_error():
    if PREVENT_ESCALATION:
        return

    error_type, e, tb = sys.exc_info()

    if getattr(e, "hypothesis_internal_never_escalate", False):
        return

    filepath = traceback.extract_tb(tb)[-1][0]
    if is_hypothesis_file(filepath) and not isinstance(
        e, (HypothesisException,) + HYPOTHESIS_CONTROL_EXCEPTIONS
    ):
        raise


def get_trimmed_traceback(exception=None):
    """Return the current traceback, minus any frames added by Hypothesis."""
    if exception is None:
        _, exception, tb = sys.exc_info()
    else:
        tb = exception.__traceback__
    # Avoid trimming the traceback if we're in verbose mode, or the error
    # was raised inside Hypothesis (and is not a MultipleFailures)
    if hypothesis.settings.default.verbosity >= hypothesis.Verbosity.debug or (
        is_hypothesis_file(traceback.extract_tb(tb)[-1][0])
        and not isinstance(exception, (Flaky, MultipleFailures))
    ):
        return tb
    while tb is not None and (
        # If the frame is from one of our files, it's been added by Hypothesis.
        is_hypothesis_file(getframeinfo(tb.tb_frame)[0])
        # But our `@proxies` decorator overrides the source location,
        # so we check for an attribute it injects into the frame too.
        or tb.tb_frame.f_globals.get("__hypothesistracebackhide__") is True
    ):
        tb = tb.tb_next
    return tb


def get_interesting_origin(exception):
    # The `interesting_origin` is how Hypothesis distinguishes between multiple
    # failures, for reporting and also to replay from the example database (even
    # if report_multiple_bugs=False).  We traditionally use the exception type and
    # location, but have extracted this logic in order to see through `except ...:`
    # blocks and understand the __cause__ (`raise x from y`) or __context__ that
    # first raised an exception.
    tb = get_trimmed_traceback(exception)
    filename, lineno, *_ = traceback.extract_tb(tb)[-1]
    return (
        type(exception),
        filename,
        lineno,
        # Note that if __cause__ is set it is always equal to __context__, explicitly
        # to support introspection when debugging, so we can use that unconditionally.
        get_interesting_origin(exception.__context__) if exception.__context__ else (),
    )
