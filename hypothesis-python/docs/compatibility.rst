Compatibility
=============

Hypothesis generally does its level best to be compatible with everything you could need it to be compatible with. This document outlines our compatibility status and guarantees.

Hypothesis versions
-------------------

Backwards compatibility is better than backporting fixes, so we use
:ref:`semantic versioning <release-policy>` and only support the most recent
version of Hypothesis.

Documented APIs will not break except between major version bumps.
All APIs mentioned in the Hypothesis documentation are public unless explicitly
noted as provisional, in which case they may be changed in minor releases.
Undocumented attributes, modules, and behaviour may include breaking
changes in patch releases.


.. _deprecation-policy:

Deprecations
------------

Deprecated features will emit warnings for at least six
months, and then be removed in the following major release.

Note however that not all warnings are subject to this grace period;
sometimes we strengthen validation by adding a warning, and these may
become errors immediately at a major release.

We use custom exception and warning types, so you can see
exactly where an error came from, or turn only our warnings into errors.

Python versions
---------------

Hypothesis is supported and tested on CPython and PyPy 3.9+, i.e. all Python versions `that are still supported <https://devguide.python.org/versions/>`_.
32-bit builds of CPython also work, though we only test them on Windows.

Hypothesis does not officially support anything except the latest patch release of each supported Python version. We will fix bugs in earlier patch releases if reported, but they're not tested in CI and no guarantees are made.

Operating systems
-----------------

In theory, Hypothesis should work anywhere that Python does. In practice, it is
known to work and regularly tested on macOS, Windows, Linux, and `Emscripten <https://peps.python.org/pep-0776/>`_.

If you experience issues running Hypothesis on other operating systems, we are
happy to accept bug reports which either clearly point to the problem or contain
reproducing instructions for a Hypothesis maintainer who does not have the ability
to run that OS. It's hard to fix something we can't reproduce!

.. _framework-compatibility:

Testing frameworks
------------------

In general, Hypothesis goes to quite a lot of effort to return a function from |@given| that behaves as closely to a normal test function as possible. This means that most things should work sensibly with most testing frameworks.

Maintainers of testing frameworks may be interested in our support for :ref:`custom function execution <custom-function-execution>`, which may make some Hypothesis interactions possible to support.

pytest
~~~~~~

The main interaction to be aware of between Hypothesis and :pypi:`pytest` is fixtures.

pytest fixtures are automatically passed to |@given| tests, as usual. Note that |@given| supplies parameters from the right, so tests which use a fixture should be written with the fixture placed first:

.. code-block:: python

  @given(st.integers())
  def test_use_fixture(myfixture, n):
      pass

However, function-scoped fixtures run only once for the entire test, not per-input. This can be surprising for fixtures which are expected to set up per-input state. To proactively warn about this, we raise |HealthCheck.function_scoped_fixture| (unless suppressed with |settings.suppress_health_check|).

unittest
~~~~~~~~

:pypi:`unittest` works out of the box with Hypothesis.

The :func:`python:unittest.mock.patch` decorator works with |@given|, but we recommend using it as a context manager within the test instead, to ensure that the mock is per-input, and to avoid poor interactions with Pytest fixtures.

Django
~~~~~~

Integration with Django's testing requires use of the :ref:`hypothesis-django` extra. The issue is that Django tests reset the database once per test, rather than once per input.

coverage.py
~~~~~~~~~~~

:pypi:`coverage` works out of the box with Hypothesis. Our own test suite has 100% branch coverage.

Nose
~~~~

:pypi:`nose` tests work with Hypothesis out of the box, except for ``yield``-based tests, which simply won't work.

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

**Running the same test in multiple threads**, or using multiple threads within the same test, makes it pretty easy to trigger internal errors.  We usually accept patches for such issues unless readability or single-thread performance suffer.

Hypothesis assumes that tests are single-threaded, or do a sufficiently-good job of pretending to be single-threaded.  Tests that use helper threads internally should be OK, but the user must be careful to ensure that test outcomes are still deterministic. In particular it counts as nondeterministic if helper-thread timing changes the sequence of dynamic draws using e.g. the |st.data| strategy.

Interacting with any Hypothesis APIs from helper threads might do weird/bad things, so avoid that too - we rely on thread-local variables in a few places, and haven't explicitly tested/audited how they respond to cross-thread API calls.  While |st.data| and equivalents are the most obvious danger, other APIs might also be subtly affected.

Type hints
----------

We ship type hints with Hypothesis itself. Though we always try to minimize breakage, we may make breaking changes to these between minor releases and do not commit to maintaining a fully stable interface for type hints.

We may also find more precise ways to describe the type of various interfaces, or change their type and runtime behaviour together in a way which is otherwise backwards-compatible.

There are known issues with inferring the type of examples generated by |st.deferred|, |st.recursive|, |st.one_of|, |st.dictionaries|, and |st.fixed_dictionaries|. We're following proposed updates to Python's typing standards, but unfortunately the long-standing interfaces of these strategies cannot (yet) be statically typechecked.
