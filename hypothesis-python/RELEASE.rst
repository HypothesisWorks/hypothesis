RELEASE_TYPE: patch

This patch fixes a rare ``RecursionError`` when pretty-printing a multi-line
object without type-specific printer, which was passed to a function which
returned the same object by ``.map()`` or :func:`~hypothesis.strategies.builds`
and thus recursed due to the new pretty reprs in Hypothesis :ref:`v6.65.0`
(:issue:`3560`).  Apologies to all those affected.
