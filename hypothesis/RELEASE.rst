RELEASE_TYPE: minor

This release allows you to use :func:`~hypothesis.strategies.data` in |@example|,
exposing a `DataObject` type which provides the drawn values in order.

Additionally, when a test using :func:`~hypothesis.strategies.data` fails,
the printed falsifying example now shows the sequence of values that were drawn via
``data.draw(...)``, rather than the opaque ``data(...)`` placeholder, which
can be used as the argument for |@example|:

.. code-block:: python

    @given(data=st.data())
    def test(data):
        x = data.draw(st.integers(), label="Something")
        ...

now reports

.. code-block:: text

    Falsifying example: test(
        data=DataObject(draws=[
            # Something
            0,
        ]),
    )

(A ``label=`` argument to ``data.draw()`` is rendered as a comment on the line above that draw)

The previous per-draw ``Draw N: value`` notes are no longer emitted, since
the same information is now inline.
