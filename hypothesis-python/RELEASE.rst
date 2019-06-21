RELEASE_TYPE: patch

This patch fixes :issue:`2014`, where our compatibility layer broke with version
3.7.4 of the :pypi:`typing` module backport on PyPI.

This issue only affects Python 2.  We remind users that Hypothesis, like many other
packages, `will drop Python 2 support on 2020-01-01 <https://python3statement.org>`__
and already has several features that are only available on Python 3.
