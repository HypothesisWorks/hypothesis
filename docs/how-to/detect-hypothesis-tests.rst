Detect Hypothesis tests
-----------------------

How to dynamically determine whether a test function has been defined with Hypothesis.

Via ``is_hypothesis_test``
~~~~~~~~~~~~~~~~~~~~~~~~~~

The most straightforward way is to use |is_hypothesis_test|:

.. code-block:: python

    from hypothesis import is_hypothesis_test

    @given(st.integers())
    def f(n): ...

    assert is_hypothesis_test(f)

This works for stateful tests as well:

.. code-block:: python

    from hypothesis import is_hypothesis_test
    from hypothesis.stateful import RuleBasedStateMachine

    class MyStateMachine(RuleBasedStateMachine): ...

    assert is_hypothesis_test(MyStateMachine.TestCase().runTest)

Via pytest
~~~~~~~~~~

If you're working with :pypi:`pytest`, the :ref:`Hypothesis pytest plugin <pytest-plugin>` automatically adds the ``@pytest.mark.hypothesis`` mark to all Hypothesis tests. You can use ``node.get_closest_marker("hypothesis")`` or similar methods to detect the existence of this mark.
