RELEASE_TYPE: minor

When a test using :func:`~hypothesis.strategies.data` fails, the printed
falsifying example now shows the sequence of values that were drawn via
``data.draw(...)``, rather than the opaque ``data(...)`` placeholder.
For example:

.. code-block:: python

    @given(data=st.data())
    def test(data):
        x = data.draw(st.integers())
        y = data.draw(st.lists(st.integers()))
        ...

may now report ``Falsifying example: test(data=DataObject(draws=[0, [0]]))``.

Each draw is rendered using the value that was drawn (not the live object),
so mutations made to drawn values after ``data.draw`` returns are not
reflected in the output.

Internally, :class:`~hypothesis.vendor.pretty.RepresentationPrinter` gains
``deferred()`` and ``finalize()`` methods, which made this feature possible
by allowing the ``draws=[...]`` list to be filled in as draws happen during
the re-run used to produce the output.
