RELEASE_TYPE: minor

When a test using :func:`~hypothesis.strategies.data` fails, the printed
falsifying example now shows the sequence of values that were drawn via
``data.draw(...)``, rather than the opaque ``data(...)`` placeholder, with
each draw on its own line. A ``label=`` argument to ``data.draw()`` is
rendered as a comment on the line above that draw. For example:

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

The previous per-draw ``Draw N: value`` notes are no longer emitted, since
the same information is now inline in the ``draws=[...]`` rendering.
