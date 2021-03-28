RELEASE_TYPE: patch

The :func:`~hypothesis.strategies.fixed_dictionaries` strategy now preserves
dict iteration order instead of sorting the keys.  This also affects the
pretty-printing of keyword arguments to :func:`@given() <hypothesis.given>`
(:issue:`2913`).
