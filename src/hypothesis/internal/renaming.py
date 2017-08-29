# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

from hypothesis._settings import note_deprecation
from hypothesis.internal.reflection import proxies


def renamed_arguments(**rename_mapping):
    """Helper function for deprecating arguments that have been renamed to a
    new form."""
    assert len(set(rename_mapping.values())) == len(rename_mapping)

    def accept(f):
        @proxies(f)
        def with_name_check(**kwargs):
            for k, v in list(kwargs.items()):
                if k in rename_mapping and v is not None:
                    t = rename_mapping[k]
                    note_deprecation((
                        'The argument %s has been renamed to %s. The old '
                        'name will go away in a future version of '
                        'Hypothesis.') % (k, t))
                    kwargs[t] = kwargs.pop(k)
            return f(**kwargs)

        # This decorates things in the public API, which all have docstrings.
        # (If they're not in the public API, we don't need a deprecation path.)
        # But docstrings are stripped when running with PYTHONOPTIMIZE=2.
        #
        # If somebody's running with that flag, they don't expect any
        # docstrings to be present, so this message isn't useful.  Absence of
        # a docstring is a strong indicator that they're running in this mode,
        # so skip adding this message if that's the case.
        if with_name_check.__doc__ is not None:
            with_name_check.__doc__ += '\n'.join((
                '', '',
                'The following arguments have been renamed:',
                '',
            ) + tuple(
                '  * %s has been renamed to %s' % s
                for s in rename_mapping.items()
            ) + (
                '',
                'Use of the old names has been deprecated and will be removed',
                'in a future version of Hypothesis.'
            )
            )

        return with_name_check
    return accept
