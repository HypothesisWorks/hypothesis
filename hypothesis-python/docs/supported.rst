=============
Compatibility
=============

Hypothesis does its level best to be compatible with everything you could
possibly need it to be compatible with. Generally you should just try it and
expect it to work. If it doesn't, you can be surprised and check this document
for the details.

---------------
Python versions
---------------

Hypothesis is supported and tested on CPython 2.7 and CPython 3.4+, i.e.
`all versisions of CPython with upstream support <https://devguide.python.org/#status-of-python-branches>`_,

Hypothesis also supports the latest PyPy for both Python 2 (until 2020) and Python 3.
Hypothesis does not currently work on Jython,
though it probably could (:issue:`174`). IronPython might work but hasn't been
tested.  32-bit and narrow builds should work, though this is currently only
tested on Windows.

In general Hypothesis does not officially support anything except the latest
patch release of any version of Python it supports. Earlier releases should work
and bugs in them will get fixed if reported, but they're not tested in CI and
no guarantees are made.

-----------------
Operating systems
-----------------

In theory Hypothesis should work anywhere that Python does. In practice it is
only known to work and regularly tested on OS X, Windows and Linux, and you may
experience issues running it elsewhere.

If you're using something else and it doesn't work, do get in touch and I'll try
to help, but unless you can come up with a way for me to run a CI server on that
operating system it probably won't stay fixed due to the inevitable march of time.

.. _framework-compatibility:

------------------
Testing frameworks
------------------

In general Hypothesis goes to quite a lot of effort to generate things that
look like normal Python test functions that behave as closely to the originals
as possible, so it should work sensibly out of the box with every test framework.

If your testing relies on doing something other than calling a function and seeing
if it raises an exception then it probably *won't* work out of the box. In particular
things like tests which return generators and expect you to do something with them
(e.g. nose's yield based tests) will not work. Use a decorator or similar to wrap the
test to take this form, or ask the framework maintainer to support our
:ref:`hooks for inserting such a wrapper later <custom-function-execution>`.

In terms of what's actually *known* to work:

  * Hypothesis integrates as smoothly with pytest and unittest as we can make it,
    and this is verified as part of the CI.
  * :pypi:`pytest` fixtures work in the usual way for tests that have been decorated
    with :func:`@given <hypothesis.given>` - just avoid passing a strategy for
    each argument that will be supplied by a fixture.  However, each fixture
    will run once for the whole function, not once per example.  Decorating a
    fixture function with :func:`@given <hypothesis.given>` is meaningless.
  * The :func:`python:unittest.mock.patch` decorator works with
    :func:`@given <hypothesis.given>`, but we recommend using it as a context
    manager within the decorated test to ensure that the mock is per-test-case
    and avoid poor interactions with Pytest fixtures.
  * Nose works fine with Hypothesis, and this is tested as part of the CI. ``yield`` based
    tests simply won't work.
  * Integration with Django's testing requires use of the :ref:`hypothesis-django` package.
    The issue is that in Django's tests' normal mode of execution it will reset the
    database once per test rather than once per example, which is not what you want.
  * :pypi:`Coverage` works out of the box with Hypothesis; our own test suite has
    100% branch coverage.

-----------------
Optional Packages
-----------------

The supported versions of optional packages, for strategies in ``hypothesis.extra``,
are listed in the documentation for that extra.  Our general goal is to support
all versions that are supported upstream.

------------------------
Regularly verifying this
------------------------

Everything mentioned above as explicitly supported is checked on every commit
with `Travis <https://travis-ci.org/HypothesisWorks/hypothesis-python>`_,
`Appveyor <https://ci.appveyor.com/project/DRMacIver/hypothesis-python/>`_, and
`CircleCI <https://circleci.com/gh/HypothesisWorks/hypothesis-python>`_.
Our continous delivery pipeline runs all of these checks before publishing
each release, so when we say they're supported we really mean it.

-------------------
Hypothesis versions
-------------------

Backwards compatibility is better than backporting fixes, so we use
:ref:`semantic versioning <release-policy>` and only support the most recent
version of Hypothesis.  See :doc:`support` for more information.
