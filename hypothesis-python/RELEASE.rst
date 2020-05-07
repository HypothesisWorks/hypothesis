RELEASE_TYPE: minor

This release improves the interaction between :func:`~hypothesis.assume`
and the :func:`@example() <hypothesis.example>` decorator, so that the
following test no longer fails with ``UnsatisfiedAssumption`` (:issue:`2125`):

.. code-block:: python

    @given(value=floats(0, 1))
    @example(value=0.56789)  # used to make the test fail!
    @pytest.mark.parametrize("threshold", [0.5, 1])
    def test_foo(threshold, value):
        assume(value < threshold)
        ...
