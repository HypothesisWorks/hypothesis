# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

try:
    EncodingWarning
except NameError:
    pass
else:
    # Work around https://github.com/numpy/numpy/issues/24115
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", EncodingWarning)  # noqa  # not undefined
        import numpy.testing  # noqa
