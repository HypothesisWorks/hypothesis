Compatibility
=============

Hypothesis does its level best to be compatible with everything you could
possibly need it to be compatible with. Generally you should just try it and
expect it to work. If it doesn't, you can be surprised and check this document
for the details.

Hypothesis versions
-------------------

Backwards compatibility is better than backporting fixes, so we use
:ref:`semantic versioning <release-policy>` and only support the most recent
version of Hypothesis.

Documented APIs will not break except between major version bumps.
All APIs mentioned in this documentation are public unless explicitly
noted as provisional, in which case they may be changed in minor releases.
Undocumented attributes, modules, and behaviour may include breaking
changes in patch releases.


.. _deprecation-policy:

Deprecations
------------

Deprecated features will emit warnings for at least six
months, and then be removed in the following major release.

Note however that not all warnings are subject to this grace period;
sometimes we strengthen validation by adding a warning and these may
become errors immediately at a major release.

We use custom exception and warning types, so you can see
exactly where an error came from, or turn only our warnings into errors.

.. autoclass:: hypothesis.errors.HypothesisDeprecationWarning


Python versions
---------------

Hypothesis is supported and tested on CPython 3.9+, i.e.
`all versions of CPython with upstream support <https://devguide.python.org/versions/>`_,
along with PyPy for the same versions.
32-bit builds of CPython also work, though we only test them on Windows.

In general Hypothesis does not officially support anything except the latest
patch release of any version of Python it supports. Earlier releases should work
and bugs in them will get fixed if reported, but they're not tested in CI and
no guarantees are made.

Operating systems
-----------------

In theory Hypothesis should work anywhere that Python does. In practice it is
only known to work and regularly tested on OS X, Windows and Linux, and you may
experience issues running it elsewhere.

If you're using something else and it doesn't work, do get in touch and I'll try
to help, but unless you can come up with a way for me to run a CI server on that
operating system it probably won't stay fixed due to the inevitable march of time.

.. _framework-compatibility:

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
  with |@given| - just avoid passing a strategy for
  each argument that will be supplied by a fixture.  However, function-scoped fixtures
  will run only once for the whole function, not per example. To proactively warn you about
  this case, we raise |HealthCheck.function_scoped_fixture|, unless suppressed with
  |settings.suppress_health_check|.
* The :func:`python:unittest.mock.patch` decorator works with
  |@given|, but we recommend using it as a context
  manager within the decorated test to ensure that the mock is per-test-case
  and avoid poor interactions with Pytest fixtures.
* Nose works fine with Hypothesis, and this is tested as part of the CI. ``yield`` based
  tests simply won't work.
* Integration with Django's testing requires use of the :ref:`hypothesis-django` extra.
  The issue is that in Django's tests' normal mode of execution it will reset the
  database once per test rather than once per example, which is not what you want.
* :pypi:`coverage` works out of the box with Hypothesis; our own test suite has
  100% branch coverage.

Optional packages
-----------------

The supported versions of optional packages, for strategies in ``hypothesis.extra``,
are listed in the documentation for that extra.  Our general goal is to support
all versions that are supported upstream.


.. _thread-safety-policy:

Thread-Safety Policy
--------------------

As of :version:`6.136.9`, Hypothesis is thread-safe. Each of the following is fully supported, and tested regularly in CI:

* Running tests in multiple processes
* Running separate tests in multiple threads
* Running the same test in multiple threads

If you find a bug here, please report it. The main risks internally are global state, shared caches, and cached strategies.

Thread usage inside tests
~~~~~~~~~~~~~~~~~~~~~~~~~

.. TODO_DOCS: link to not-yet-merged flaky failure tutorial page

Tests that spawn threads internally are supported by Hypothesis.

However, these as with any Hypothesis test, these tests must have deterministic test outcomes and data generation. For example, if timing changes in the threads change the sequence of dynamic draws from |st.composite| or |st.data|, Hypothesis may report the test as flaky. The solution here is to refactor data generation so it does not depend on test timings.

Cross-thread API calls
~~~~~~~~~~~~~~~~~~~~~~

In theory, Hypothesis supports cross-thread API calls, for instance spawning a thread inside of a test and using that to draw from |st.composite| or |st.data|, or to call |event|, |target|, or |assume|.

However, we have not explicitly audited this behavior, and do not regularly test it in our CI. If you find a bug here, please report it. If our investigation determines that we cannot support cross-thread calls for the feature in question, we will update this page accordingly.

Type hints
----------

We ship type hints with Hypothesis itself. Though we always try to minimize breakage, we may make breaking changes to these between minor releases and do not commit to maintaining a fully stable interface for type hints.

We may also find more precise ways to describe the type of various interfaces, or change their type and runtime behaviour together in a way which is otherwise backwards-compatible.

There are known issues with inferring the type of examples generated by |st.deferred|, |st.recursive|, |st.one_of|, |st.dictionaries|, and |st.fixed_dictionaries|. We're following proposed updates to Python's typing standards, but unfortunately the long-standing interfaces of these strategies cannot (yet) be statically typechecked.
