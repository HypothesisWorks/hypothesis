.. _custom-function-execution:

Custom function execution
-------------------------

Hypothesis provides you with a hook that lets you control how it runs examples.

This lets you do things like set up and tear down around each example, run examples in a subprocess, transform coroutine tests into normal tests, etc. For example, :class:`~hypothesis.extra.django.TransactionTestCase` in the Django extra runs each example in a separate database transaction.

The way this works is by introducing the concept of an executor. An executor is essentially a function that takes a block of code and run it. The default executor is:

.. code:: python

    def default_executor(function):
        return function()

You define executors by defining a method ``execute_example`` on a class. Any test methods on that class with :func:`@given <hypothesis.given>` used on them will use ``self.execute_example`` as an executor with which to run tests. For example, the following executor runs all its code twice:

.. code:: python

    from unittest import TestCase


    class TestTryReallyHard(TestCase):
        @given(integers())
        def test_something(self, i):
            perform_some_unreliable_operation(i)

        def execute_example(self, f):
            f()
            return f()

Note: The functions you use in map, etc. will run *inside* the executor. i.e. they will not be called until you invoke the function passed to ``execute_example``.

An executor must be able to handle being passed a function which returns None, otherwise it won't be able to run normal test cases. So for example the following executor is invalid:

.. code:: python

    from unittest import TestCase


    class TestRunTwice(TestCase):
        def execute_example(self, f):
            return f()()

and should be rewritten as:

.. code:: python

    from unittest import TestCase


    class TestRunTwice(TestCase):
        def execute_example(self, f):
            result = f()
            if callable(result):
                result = result()
            return result


An alternative hook is provided for use by test runner extensions such as :pypi:`pytest-trio`, which cannot use the ``execute_example`` method. This is **not** recommended for end-users - it is better to write a complete test function directly, perhaps by using a decorator to perform the same transformation before applying :func:`@given <hypothesis.given>`.

.. code:: python

    @given(x=integers())
    @pytest.mark.trio
    async def test(x): ...


    # Illustrative code, inside the pytest-trio plugin
    test.hypothesis.inner_test = lambda x: trio.run(test, x)

For authors of test runners however, assigning to the ``inner_test`` attribute of the ``hypothesis`` attribute of the test will replace the interior test.

.. note::
    The new ``inner_test`` must accept and pass through all the ``*args``
    and ``**kwargs`` expected by the original test.

If the end user has also specified a custom executor using the ``execute_example`` method, it - and all other execution-time logic - will be applied to the *new* inner test assigned by the test runner.
