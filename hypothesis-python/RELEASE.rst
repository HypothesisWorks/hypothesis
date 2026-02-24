RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.stateful.consumes` so that
``consumes(bundle).flatmap(...)`` no longer raises :class:`TypeError`.
Previously, :class:`~hypothesis.stateful.Bundle.flatmap` used ``type(self)(...)``
to construct the result, which would create a ``BundleConsumer`` with an
incompatible ``__init__`` signature. Now uses ``Bundle(...)`` directly.
