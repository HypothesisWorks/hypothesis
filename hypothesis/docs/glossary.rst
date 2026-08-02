Glossary
========

User glossary
-------------

Terms that are part of our public API.

.. glossary::

    explicit example
        A |test case| from |@example|.

        .. code-block:: python

            @example(42)
            def f(n):
                pass

        Here, ``42`` is an explicit example.

        Explicit examples are always run, in the |Phase.explicit| phase. Unlike Hypothesis-generated test cases, Hypothesis does not shrink explicit examples.

    failing test case
        A |test case| which causes the test to fail, usually by causing an exception to be raised.

    minimal failing test case
        The |failing test case| which has been fully shrunk (minimized) by Hypothesis. Hypothesis reports only the minimal failing test case to the user at the end of the test.

        .. code-block:: python

            @given(st.integers())
            def f(n):
                print("called with", n)
                assert n < 10

        .. code-block:: none

            called with 0
            called with 921
            called with 212
            ...
            called with 10
            ...
            Failing test case: f(
                n=10,
            )

        Here, each of ``921``, ``212``, and ``10`` are failing test cases. ``10`` is the minimal failing test case.

    test case
        The Hypothesis-generated input to a test function.

        .. code-block:: python

            @given(st.integers())
            def f(n):
                print("called with", n)
                assume(n >= 0)

        .. code-block:: none

            called with 0
            called with 18588
            called with 672780074
            called with -32616
            ...

        Here, the first four test cases are ``0``, ``18588``, ``672780074``, and ``-32616``.

        "Test case" may also refer to the resulting execution of an input in a test function. Above, we might say that "the test case ``-32616`` failed the |assume|", referring to its entire execution.


Developer glossary
------------------

Terms that are part of our developer API. The developer API is intended for advanced users, researchers, and developers building on top of Hypothesis.

.. glossary::

    choice sequence
        The underlying sequence of primitive values corresponding to a :term:`test case`. Conceptually, a choice sequence is the sequence of random choices made in the course of generating a value in a strategy. Each test case is represented internally as a choice sequence.

        The exact representation is an implementation detail and depends on the strategy. For example, the value ``True`` from |st.booleans| is represented by the choice sequence ``[True]``, while the value ``[2, 42]`` from ``st.lists(st.integers())`` is represented by the choice sequence ``[True, 2, True, 42, False]``.

        Currently, a choice sequence consists of booleans, integers, floats, strings, and bytes.
