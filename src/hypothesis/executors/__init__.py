# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""The executors package defines ways to run your code that are more involved
than simple function invocation.

It defines the idea of an executor: An executor takes two functions. One may
be called to produce an example, the other is a test to pass the example to.

Examples are pairs (args, kwargs) which should be passed to the test as
test(*args, **kwargs)

Executors are created by calling the executor ExtMethod on the object. The
default implementation looks for execute_example, which much be an executor,
and if that is not found looks for setup_example and teardown_example and
creates an executor that uses invokes those.

This interface is experimental and should be considered semi-public, in the
sense that it won't break in patch versions but may break between minor
versions. However the way it is set up means that it should be relatively easy
to make old code work automatically in it, so it will probably not break
between minor versions either.

"""


from .executors import executor, default_executor

__all__ = ['executor', 'default_executor']
