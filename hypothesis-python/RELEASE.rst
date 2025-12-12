RELEASE_TYPE: minor

This release adds |settings.observability|, which can be used to enable :ref:`observability <observability>`.

When observability is enabled, Hypothesis writes data about each test case to the ``.hypothesis/observed`` directory in an analysis-ready `jsonlines <https://jsonlines.org/>`_ format. This data is intended to help users who want to dive deep into understanding their tests. It's also intended for people building tools or research on top of Hypothesis.

Observability can be controlled in two ways:

* via the new |settings.observability| argument,
* or via the ``HYPOTHESIS_OBSERVABILITY`` environment variable.

See :ref:`Configuring observability <observability-configuration>` for details.

If you use VSCode, we recommend the `Tyche <https://github.com/tyche-pbt/tyche-extension>`__ extension, a PBT-specific visualization tool designed for Hypothesis's observability interface.
