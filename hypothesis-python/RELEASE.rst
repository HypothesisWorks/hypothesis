RELEASE_TYPE: minor

This release extends the explain-phase ``# or any other generated value`` comments
to sub-arguments within :func:`~hypothesis.strategies.builds`,
:func:`~hypothesis.strategies.tuples`, and :func:`~hypothesis.strategies.fixed_dictionaries`.

Previously, these comments only appeared on top-level test arguments. Now, when
the explain phase determines that a sub-argument can vary freely without affecting
the test failure, you'll see comments like::

    Falsifying example: test_foo(
        obj=MyClass(
            x=0,  # or any other generated value
            y=True,
        ),
        data=(
            '',  # or any other generated value
            42,
        ),
    )

This makes it easier to understand which parts of complex inputs actually matter
for reproducing a failure.
