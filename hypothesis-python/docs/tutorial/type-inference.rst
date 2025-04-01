Type inference for strategies
=============================

|st.builds|
-----------

|st.builds| is a strategy which lets you create instances of a class (or other callable) by passing strategies for each argument.

For example, suppose we have written a class:

.. code-block:: python

    class MyClass:
        def __init__(self, a, *, b):
            self.a = a
            self.b = b

|st.builds| lets us define a strategy which creates ``MyClass`` instances, by passing strategies for ``a`` and ``b``:

.. code-block:: python

    @given(st.builds(MyClass, st.integers(), b=st.floats()))
    def test_my_class(obj):
        assert isinstance(obj, MyClass)
        assert isinstance(obj.a, int)
        assert isinstance(obj.b, float)

Type inference
~~~~~~~~~~~~~~

|st.builds| automatically infers strategies based on type annotations. If the argument is annotated with ``x: int``, |st.builds| will use the |st.integers| strategy; if ``x: float`` then it will use the |st.floats| strategy; etc.

.. note::

    This type inference uses |st.from_type|. See the |st.from_type| and |st.register_type_strategy| documentation for how to control type inference in Hypothesis.

.. code-block:: python

    class MyClass:
        def __init__(self, a: int, *, b: float):
            self.a = a
            self.b = b

    @given(st.builds(MyClass))
    def test_my_class(obj):
        assert isinstance(obj, MyClass)
        assert isinstance(obj.a, int)
        assert isinstance(obj.b, float)

You can still override the automatic inference if you want. For instance, we can change the ``b`` parameter to only generate positive floats, while still leaving ``a`` inferred:

.. code-block:: python

    class MyClass:
        def __init__(self, a: int, *, b: float):
            self.a = a
            self.b = b

    # changed
    @given(st.builds(MyClass, b=st.floats(min_value=0.0)))
    def test_my_class(obj):
        assert isinstance(obj, MyClass)
        assert isinstance(obj.a, int)
        assert isinstance(obj.b, float)
        # added
        assert obj.b > 0.0

This type inference also works for |dataclasses| and :pypi:`attrs` classes.
