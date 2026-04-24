RELEASE_TYPE: minor

When a test using :func:`~hypothesis.strategies.data` fails, the printed
falsifying example now shows the sequence of values that were drawn via
``data.draw(...)``, rather than the opaque ``data(...)`` placeholder, with
each draw on its own line. A ``label=`` argument to ``data.draw()`` is
rendered as a comment on the line above that draw. For example:

.. code-block:: python

    @given(data=st.data())
    def test(data):
        x = data.draw(st.integers(), label="Cool thing")
        ...

now reports

.. code-block:: text

    Falsifying example: test(
        data=DataObject(draws=[
            # Cool thing
            0,
        ]),
    )

The previous per-draw ``Draw N: value`` notes are no longer emitted, since
the same information is now inline in the ``draws=[...]`` rendering.

Each draw is captured using the value as it was when drawn, so mutations
made to drawn values after ``data.draw`` returns are not reflected in the
output.

Internally, :class:`~hypothesis.vendor.pretty.RepresentationPrinter` gains
``deferred()`` and ``finalize()`` methods, which made this feature possible
by allowing the ``draws=[...]`` list to be filled in as draws happen during
the re-run used to produce the output.
