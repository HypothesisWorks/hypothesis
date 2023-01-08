RELEASE_TYPE: minor

A classic error when testing is to write a test function that can never fail,
even on inputs that aren't allowed or manually provided.  By analogy to the
design pattern of::

    @pytest.mark.parametrize("arg", [
        ...,  # passing examples
        pytest.param(..., marks=[pytest.mark.xfail])  # expected-failing input
    ])

we now support :obj:`@example(...).xfail() <hypothesis.example.xfail>`, with
the same (optional) ``condition``, ``reason``, and ``raises`` arguments as
``pytest.mark.xfail()``.

Naturally you can also write ``.via(...).xfail(...)``, or ``.xfail(...).via(...)``,
if you wish to note the provenance of expected-failing examples.
