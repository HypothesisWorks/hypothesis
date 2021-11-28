RELEASE_TYPE: patch

This release fixes :issue:`3080`, where :func:`~hypothesis.strategies.from_type`
failed on unions containing :pep:`585` builtin generic types (like ``list[int]``)
in Python 3.9 and later.
