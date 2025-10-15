RELEASE_TYPE: minor

This release stabilizes our :ref:`observability interface <observability>`, which was previously marked as experimental. When observability is enabled, Hypothesis writes data about each test case to ``.hypothesis/observed`` in an analysis-ready `jsonlines <https://jsonlines.org/>`_ format, intended to help you understand the performance of your Hypothesis tests.

Observability can be controlled in two ways:

* via the new |settings.observability| argument,
* or via the ``HYPOTHESIS_OBSERVABILITY`` environment variable.

See :ref:`Configuring observability <observability-configuration>` for details.

If you use VSCode, we recommend the `Tyche <https://github.com/tyche-pbt/tyche-extension>`__ extension, a PBT-specific visualization tool designed for Hypothesis's observability interface.
