RELEASE_TYPE: patch

If you were running Python 3.13 (currently in alpha) with :pypi:`pytest-xdist`
and then attempted to pretty-print a ``lambda`` functions which was created
using the :func:`eval` builtin, it would have raised an AssertionError.
Now you'll get ``"lambda ...: <unknown>"``, as expected.
