RELEASE_TYPE: patch

Tests using :func:`@given <hypothesis.given>` now shrink errors raised from
:pypi:`pytest` helper functions, instead of reporting the first example found.

This was previously fixed in :ref:`version 3.56.0 <v3.56.0>`, but only for
stateful testing.
