Quickstart
==========

This is a lightning introduction to the most important features of Hypothesis; enough to get you started writing tests. The :doc:`tutorial <tutorial/index>` introduces these features (and more) in greater detail.

Install Hypothesis
------------------

.. code-block:: shell

    pip install hypothesis


Write your first test
---------------------

Create a new file called ``example.py``, containing a simple test:

.. code-block:: python

    # contents of example.py
    from hypothesis import given, strategies as st

    @given(st.integers())
    def test_integers(n):
        print(f"called with {n}")
        assert isinstance(n, int)

    test_integers()

|@given| is the standard entrypoint to Hypothesis. It takes a *strategy*, which describes the type of inputs you want the decorated function to accept. When we call ``test_integers``, Hypothesis will generate random integers (because we used the |st.integers| strategy) and pass them as ``n``. Let's see that in action now by running ``python example.py``:

.. code-block:: none

    called with 0
    called with -18588
    called with -672780074
    called with 32616
    ...

We can just call ``test_integers()``, without passing a value for ``n``, because Hypothesis takes care of generating values of ``n`` for us.

.. note::

    By default, Hypothesis generates 100 random examples. You can control this with the |max_examples| setting.

Running in a test suite
-----------------------

A Hypothesis test is still a regular python function, which means pytest or unittest will pick it up and run it in all the normal ways.

.. code-block:: python

    # contents of example.py
    from hypothesis import given, strategies as st

    @given(st.integers(0, 200))
    def test_integers(n):
        assert n < 50

This test will clearly fail, which can be confirmed by running ``pytest example.py``:

.. code-block:: none

    $ pytest example.py

        ...

        @given(st.integers())
        def test_integers(n):
    >       assert n < 50
    E       assert 50 < 50
    E       Falsifying example: test_integers(
    E           n=50,
    E       )


Arguments to |@given|
---------------------

You can pass multiple arguments to |@given|:

.. code-block:: python

    @given(st.integers(), st.text())
    def test_integers(n, s):
        assert isinstance(n, int)
        assert isinstance(s, str)

Or use keyword arguments:

.. code-block:: python

    @given(n=st.integers(), s=st.text())
    def test_integers(n, s):
        assert isinstance(n, int)
        assert isinstance(s, str)

.. note::

    See |@given| for details about how |@given| handles different types of arguments.

Filtering inside a test
-----------------------

Sometimes, you need to remove invalid cases from your test. The best way to do this is with |.filter|:

.. code-block:: python

    @given(st.integers().filter(lambda n: n % 2 == 0))
    def test_integers(n):
        assert n % 2 == 0

For more complicated conditions, you can use |assume|, which tells Hypothesis to discard any test case with a false-y argument:

.. code-block:: python

    @given(st.integers(), st.integers())
    def test_integers(n1, n2):
        assume(n1 != n2)
        # n1 and n2 are guaranteed to be different here

.. note::

    You can learn more about |.filter| and |assume| in the :doc:`/tutorial/adapting-strategies` tutorial page.

Dependent generation
--------------------

You may want an input to depend on the value of another input. For instance, you might want to generate two integers ``n1`` and ``n2`` where ``n1 <= n2``.

You can do this using the |st.composite| strategy. |st.composite| lets you define a new strategy which is itself built by drawing values from other strategies, using the automatically-passed ``draw`` function.

.. code-block:: python

    @st.composite
    def ordered_pairs(draw):
        n1 = draw(st.integers())
        n2 = draw(st.integers(min_value=n1))
        return (n1, n2)

    @given(ordered_pairs())
    def test_pairs_are_ordered(pair):
        n1, n2 = pair
        assert n1 <= n2

In more complex cases, you might need to interleave generation and test code. In this case, use |st.data|.

.. code-block:: python

    @given(st.data(), st.text(min_size=1))
    def test_string_characters_are_substrings(data, string):
        assert isinstance(string, str)
        index = data.draw(st.integers(0, len(string) - 1))
        assert string[index] in string

Combining Hypothesis with pytest
--------------------------------

Hypothesis works with pytest features, like :ref:`pytest:pytest.mark.parametrize ref`:

.. code-block:: python

    import pytest

    from hypothesis import given, strategies as st

    @pytest.mark.parametrize("operation", [reversed, sorted])
    @given(st.lists(st.integers()))
    def test_list_operation_preserves_length(operation, lst):
        assert len(lst) == len(list(operation(lst)))

Hypothesis also works with pytest fixtures:

.. code-block:: python

    import pytest

    @pytest.fixture(scope="session")
    def shared_mapping():
        return {n: 0 for n in range(101)}

    @given(st.integers(0, 100))
    def test_shared_mapping_keys(shared_mapping, n):
        assert n in shared_mapping
