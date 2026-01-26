RELEASE_TYPE: minor

This release adds :ref:`observability <observability>`, a new feature in Hypothesis.

Observability is intended for those who want to dig into the raw data from tests or strategies—including those building tools or research on top of Hypothesis.

When observability is enabled, Hypothesis writes data about each test case to the ``.hypothesis/observed`` directory in an analysis-ready `jsonlines <https://jsonlines.org/>`_ format. This data includes a timing breakdown, coverage data, a representation of each argument, the result of any |assume| or |.filter| calls, and any other data we think is useful for analysis. See :ref:`observability <observability>` for the full data format.

Observability can be controlled in two ways:

* via the new |settings.observability| argument,
* or via the new ``HYPOTHESIS_OBSERVABILITY`` environment variable.

See :ref:`Configuring observability <observability-configuration>` for details.

If you use VSCode, we recommend the `Tyche <https://github.com/tyche-pbt/tyche-extension>`__ extension, a PBT-specific visualization tool designed for Hypothesis's observability interface.

(Note that Hypothesis has had an implementation of observability for a number of months, which was marked as experimental. This release brings observability into our public API, and removes that experimental label.)
