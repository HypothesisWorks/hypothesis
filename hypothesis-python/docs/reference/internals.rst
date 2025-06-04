Hypothesis internals
====================

.. warning::

    This page documents internal Hypothesis interfaces. Some are fairly stable, while others are still experimental. In either case, they are not subject to our standard :ref:`deprecation policy <deprecation-policy>`, and we might make breaking changes in minor or patch releases.

    This page is intended for people building tools, libraries, or research on top of Hypothesis. If that includes you, please get in touch! We'd love to hear what you're doing, or explore more stable ways to support your use-case.

.. _alternative-backends-internals:

Alternative backends
--------------------

.. seealso::

    See also the user-facing :ref:`alternative-backends` documentation.

.. autoclass:: hypothesis.internal.conjecture.providers.PrimitiveProvider
    :members:

.. autodata:: hypothesis.internal.conjecture.providers.AVAILABLE_PROVIDERS
    :no-value:

.. autofunction:: hypothesis.internal.conjecture.provider_conformance.run_conformance_test

.. autoclass:: hypothesis.errors.BackendCannotProceed
.. autoclass:: hypothesis.internal.intervalsets.IntervalSet

Observability
-------------

.. autodata:: hypothesis.internal.observability.TESTCASE_CALLBACKS
.. autodata:: hypothesis.internal.observability.OBSERVABILITY_COLLECT_COVERAGE
.. autodata:: hypothesis.internal.observability.OBSERVABILITY_CHOICE_NODES

Engine constants
----------------

We pick reasonable values for these constants, but if you must, you can monkeypatch them. (Hypothesis is not responsible for any performance degradation that may result).

.. autodata:: hypothesis.internal.conjecture.engine.MAX_SHRINKS
.. autodata:: hypothesis.internal.conjecture.engine.MAX_SHRINKING_SECONDS
.. autodata:: hypothesis.internal.conjecture.engine.BUFFER_SIZE
