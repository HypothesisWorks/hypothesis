Low-level Reference
===================

.. warning::

    This page documents various low level Hypothesis interfaces. Some are fairly stable, while others are still experimental. In either case, they are not subject to our standard :ref:`deprecation policy <deprecation-policy>`, and we might make breaking changes in minor or patch releases.

    This page is intended for power users, and people building tools, libraries, or research on top of Hypothesis. If that includes you, please get in touch! We'd love to hear what you're doing, or explore more stable ways to support your use-case.

Low-level API
-------------

.. note::

    The ``hypothesis.lowlevel`` module contains low level APIs. ``hypothesis.lowlevel`` is intended for power uses of Hypothesis, and trades off ergonomics and safety for power and control.

    ``hypothesis.lowlevel`` is stable, but is subject to a slightly weaker policy than our standard :ref:`our deprecation policy <deprecation-policy>`. ``hypothesis.lowevel`` is subject to the following stability policy:

    * Breaking changes will be preceded by at least 3 months of a deprecation warning.
    * After the 3 month period, breaking changes may occur during any of a patch, minor, or major release.
    * Breaking changes may be made during a major release without the 3 month deprecation notice.

.. automodule:: hypothesis.lowlevel

.. autofunction:: hypothesis.lowlevel.weighted_booleans
.. autoclass:: hypothesis.lowlevel.many
    :members:

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

.. autofunction:: hypothesis.internal.observability.add_observability_callback
.. autofunction:: hypothesis.internal.observability.remove_observability_callback
.. autofunction:: hypothesis.internal.observability.with_observability_callback
.. autofunction:: hypothesis.internal.observability.observability_enabled

.. autodata:: hypothesis.internal.observability.TESTCASE_CALLBACKS
.. autodata:: hypothesis.internal.observability.OBSERVABILITY_COLLECT_COVERAGE
.. autodata:: hypothesis.internal.observability.OBSERVABILITY_CHOICES

Engine constants
----------------

We pick reasonable values for these constants, but if you must, you can monkeypatch them. (Hypothesis is not responsible for any performance degradation that may result).

.. autodata:: hypothesis.internal.conjecture.engine.MAX_SHRINKS
.. autodata:: hypothesis.internal.conjecture.engine.MAX_SHRINKING_SECONDS
.. autodata:: hypothesis.internal.conjecture.engine.BUFFER_SIZE
