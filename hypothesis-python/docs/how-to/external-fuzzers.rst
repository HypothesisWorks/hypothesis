Use Hypothesis with an external fuzzer
======================================

Sometimes you might want to point a traditional fuzzer like `python-afl <https://github.com/jwilk/python-afl>`__ or Google's :pypi:`atheris` at your code, to get coverage-guided exploration of native C extensions.  The associated tooling is often much less mature than property-based testing libraries though, so you might want to use Hypothesis strategies to describe your input data, and our world-class shrinking and :ref:`observability <observability>` tools to wrangle the results.  That's exactly what this how-to guide is about!

.. note::

    If you already have Hypothesis tests and want to fuzz them, or are targeting pure Python code, we strongly recommend the purpose-built `HypoFuzz <https://hypofuzz.com/>`_.
    This page is about writing traditional 'fuzz harnesses' with an external fuzzer, using parts of Hypothesis.

In order to support this workflow, Hypothesis exposes the |fuzz_one_input| method. |fuzz_one_input| takes a bytestring, parses it into a test case, and executes the corresponding test once. This means you can treat each of your Hypothesis tests as a traditional fuzz target, by pointing the fuzzer at |fuzz_one_input|.

For example:

.. code-block:: python

    from hypothesis import given, strategies as st

    @given(st.integers())
    def test_ints(n):
        pass

    # this parses the bytestring into a test case using st.integers(),
    # and then executes `test_ints` once.
    test_ints.hypothesis.fuzz_one_input(b"\x00" * 50)

Note that |fuzz_one_input| bypasses the standard test lifecycle. In a standard test run, Hypothesis is responsible for managing the lifecycle of a test, for example by moving between each |Phase|. In contrast, |fuzz_one_input| executes one test case, independent of this lifecycle.

See the documentation of |fuzz_one_input| for details of how it interacts with other features of Hypothesis, such as |@settings|.

Worked example: using Atheris
-----------------------------

Here is an example that uses |fuzz_one_input| with the `Atheris <https://github.com/google/atheris>`__ coverage-guided fuzzer (which is built on top of `libFuzzer <https://llvm.org/docs/LibFuzzer.html>`_):

.. code-block:: python

    import json
    import sys

    import atheris

    from hypothesis import given, strategies as st

    @given(
        st.recursive(
            st.none() | st.booleans() | st.integers() | st.floats() | st.text(),
            lambda j: st.lists(j) | st.dictionaries(st.text(), j),
        )
    )
    def test_json_dumps_valid_json(value):
        json.dumps(value)

    atheris.Setup(sys.argv, test_json_dumps_valid_json.hypothesis.fuzz_one_input)
    atheris.Fuzz()

Generating valid JSON objects based only on Atheris' ``FuzzDataProvider`` interface would be considerably more difficult.

You may also want to use ``atheris.instrument_all`` or ``atheris.instrument_imports`` in order to add coverage instrumentation to Atheris.  See the `Atheris <https://github.com/google/atheris>`__ documentation for full details.
