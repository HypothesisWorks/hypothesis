Use an external fuzzer with Hypothesis
======================================

.. seealso::

    If you're looking to fuzz property-based tests, `HypoFuzz <https://hypofuzz.com/>`_ is a coverage-guided fuzzer built for Hypothesis.

In a standard Hypothesis test run, Hypothesis is responsible for generating each test case. However, you might instead want to point a traditional fuzzer at your code, such as `python-afl <https://github.com/jwilk/python-afl>`__ or Google's :pypi:`atheris` (which instruments both Python and native extensions).

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

Using Atheris with |fuzz_one_input|
-----------------------------------

Here is an example that uses the `Atheris <https://github.com/google/atheris>`__ coverage-guided fuzzer (which is built on top of `libFuzzer <https://llvm.org/docs/LibFuzzer.html>`_) with |fuzz_one_input|:

.. code-block:: python

    import json
    import sys

    import atheris

    from hypothesis import given, strategies as st

    json_strategy = st.deferred(lambda: st.none() | st.floats() | st.text() | lists)
    lists = st.lists(json_strategy)

    @given(json_strategy)
    def test_json_dums_valid_json(value):
        json.dumps(value)

    atheris.Setup(sys.argv, test_json_dums_valid_json.hypothesis.fuzz_one_input)
    atheris.Fuzz()

You may also want to use ``atheris.instrument_all`` or ``atheris.instrument_imports`` in order to add coverage instrumentation to Atheris. For example, to instrument the ``json`` module for coverage:


.. code-block:: python

    ...

    import atheris

    with atheris.instrument_imports():
        import json  # fmt: off

    ...

See the `Atheris <https://github.com/google/atheris>`__ documentation for full details.
