.. _fuzz_one_input:

Use with external fuzzers
=========================

.. tip::

    | Want an integrated workflow for your team's local tests, CI, and continuous fuzzing?
    | Use `HypoFuzz <https://hypofuzz.com/>`__ to fuzz your whole test suite, and find more bugs without more tests!

Sometimes, you might want to point a traditional fuzzer such as `python-afl <https://github.com/jwilk/python-afl>`__, :pypi:`pythonfuzz`, or Google's :pypi:`atheris` (for Python *and* native extensions) at your code. Wouldn't it be nice if you could use any of your |@given| tests as fuzz targets, instead of converting bytestrings into your objects by hand?

.. code:: python

    @given(st.text())
    def test_foo(s): ...


    # This is a traditional fuzz target - call it with a bytestring,
    # or a binary IO object, and it runs the test once.
    fuzz_target = test_foo.hypothesis.fuzz_one_input

    # For example:
    fuzz_target(b"\x00\x00\x00\x00\x00\x00\x00\x00")
    fuzz_target(io.BytesIO(...))

Depending on the input to ``fuzz_one_input``, one of three things will happen:

- If the bytestring was invalid, for example because it was too short or
  failed a filter or :func:`~hypothesis.assume` too many times,
  ``fuzz_one_input`` returns ``None``.

- If the bytestring was valid and the test passed, ``fuzz_one_input`` returns a canonicalised and pruned buffer which will replay that test case.  This is provided as an option to improve the performance of mutating fuzzers, but can safely be ignored.

- If the test *failed*, i.e. raised an exception, ``fuzz_one_input`` will add the pruned buffer to :doc:`the Hypothesis example database <database>` and then re-raise that exception.  All you need to do to reproduce, minimize, and de-duplicate all the failures found via fuzzing is run your test suite!

Note that the interpretation of both input and output bytestrings is specific to the exact version of Hypothesis you are using and the strategies given to the test, just like the :doc:`example database <database>` and :func:`@reproduce_failure <hypothesis.reproduce_failure>` decorator.

.. tip::

  For usages of ``fuzz_one_input`` which expect to discover many failures, consider wrapping your database with :class:`~hypothesis.database.BackgroundWriteDatabase` for low-overhead writes of failures.

Interaction with settings
-------------------------

``fuzz_one_input`` uses just enough of Hypothesis' internals to drive your test function with a fuzzer-provided bytestring, and most settings therefore have no effect in this mode.  We recommend running your tests the usual way before fuzzing to get the benefits of healthchecks, as well as afterwards to replay, shrink, deduplicate, and report whatever errors were discovered.

- The :obj:`~hypothesis.settings.database` setting *is* used by fuzzing mode - adding failures to the database to be replayed when you next run your tests is our preferred reporting mechanism and response to `the 'fuzzer taming' problem <https://blog.regehr.org/archives/925>`__.
- The :obj:`~hypothesis.settings.verbosity` and :obj:`~hypothesis.settings.stateful_step_count` settings work as usual.

The |settings.deadline|, |settings.derandomize|, |settings.max_examples|, |settings.phases|, |settings.print_blob|, |settings.report_multiple_bugs|, and |settings.suppress_health_check| settings do not affect fuzzing mode.
