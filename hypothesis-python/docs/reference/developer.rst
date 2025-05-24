Developer Reference
===================

.. warning::

    This page documents APIs that Hypothesis makes available to developers building tools, libraries, or research on top of Hypothesis. It is not intended for users of Hypothesis.

    While these APIs are mostly stable, they are considered internal, and are not subject to our standard :ref:`deprecation policy <deprecation-policy>`. We may make breaking changes to these APIs in minor or patch releases.

Alternative backends
--------------------

.. autoclass:: hypothesis.internal.conjecture.providers.PrimitiveProvider
    :members:
    :undoc-members:

.. autodata:: hypothesis.internal.conjecture.providers.AVAILABLE_PROVIDERS
    :no-value:

.. autoclass:: hypothesis.errors.BackendCannotProceed

Engine constants
----------------

We pick reasonable values for these constants, but if you must, you can monkeypatch them. (Hypothesis is not responsible for any performance degradation that may result).

.. autodata:: hypothesis.internal.conjecture.engine.MAX_SHRINKS
.. autodata:: hypothesis.internal.conjecture.engine.MAX_SHRINKING_SECONDS
.. autodata:: hypothesis.internal.conjecture.engine.BUFFER_SIZE
