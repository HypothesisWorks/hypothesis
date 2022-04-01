RELEASE_TYPE: patch

This patch simplifies the repr of the strategies namespace returned in
:func:`~hypothesis.extra.array_api.make_strategies_namespace`, e.g.

.. code-block:: pycon

    >>> from hypothesis.extra.array_api import make_strategies_namespace
    >>> from numpy import array_api as xp
    >>> xps = make_strategies_namespace(xp)
    >>> xps
    make_strategies_namespace(numpy.array_api)

