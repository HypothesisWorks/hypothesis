# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import os
import warnings
from pathlib import Path

import hypothesis
from hypothesis.errors import HypothesisSideeffectWarning

__hypothesis_home_directory_default = Path.cwd() / ".hypothesis"

__hypothesis_home_directory = None


def set_hypothesis_home_dir(directory):
    global __hypothesis_home_directory
    __hypothesis_home_directory = None if directory is None else Path(directory)


def storage_directory(*names, intent_to_write=True):
    if intent_to_write and sideeffect_should_warn():
        warnings.warn(
            "Accessing the storage directory during import or initialization is "
            "discouraged, as it may cause the .hypothesis directory to be created "
            "even if hypothesis is not actually used. Typically, the fix will be "
            "to defer initialization of strategies.",
            HypothesisSideeffectWarning,
            stacklevel=2,
        )

    global __hypothesis_home_directory
    if not __hypothesis_home_directory:
        if where := os.getenv("HYPOTHESIS_STORAGE_DIRECTORY"):
            __hypothesis_home_directory = Path(where)
    if not __hypothesis_home_directory:
        __hypothesis_home_directory = __hypothesis_home_directory_default
    return __hypothesis_home_directory.joinpath(*names)


def _sideeffect_never_warn():
    return False


if os.environ.get("HYPOTHESIS_WARN_SIDEEFFECT"):

    def sideeffect_should_warn():
        return True

else:

    def sideeffect_should_warn():
        if hasattr(hypothesis, "_is_importing"):
            return True
        else:
            # We are no longer importing, patch this method to always return False from now on.
            global sideeffect_should_warn
            sideeffect_should_warn = _sideeffect_never_warn
            return False


def has_sideeffect_should_warn_been_called_after_import():
    """We warn automatically if sideeffects are induced during import.
    For sideeffects during initialization but after import, e.g. in pytest
    plugins, this method can be used to show a catch-all warning at
    start of session."""
    return sideeffect_should_warn == _sideeffect_never_warn
