RELEASE_TYPE: minor

:gh-file:`Our style guide <guides/api-style.rst>` suggests that optional
parameters should usually be keyword-only arguments (see :pep:`3102`) to
prevent confusion based on positional arguments - for example,
:func:`hypothesis.strategies.floats` takes up to *four* boolean flags
and many of the Numpy strategies have both ``dims`` and ``side`` bounds.

This release converts most optional parameters in our API to use
keyword-only arguments - and adds a compatibility shim so you get
warnings rather than errors everywhere (:issue:`2130`).
