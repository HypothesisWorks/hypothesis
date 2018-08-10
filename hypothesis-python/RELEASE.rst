RELEASE_TYPE: minor

This release adds a ``width`` argument to :func:`~hypothesis.strategies.floats`,
to generate lower-precision floating point numbers for e.g. Numpy arrays.

The generated examples are always instances of Python's native ``float``
type, which is 64bit, but passing ``width=32`` will ensure that all values
can be exactly represented as 32bit floats.  This can be useful to avoid
overflow (to +/- infinity), and for efficiency of generation and shrinking.

Half-precision floats (``width=16``) are also supported, but require Numpy
if you are running Python 3.5 or earlier.
