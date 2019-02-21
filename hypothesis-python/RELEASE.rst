RELEASE_TYPE: minor

This patch allows :func:`~hypothesis.extra.numpy.array_shapes` to generate shapes
with side-length or even dimension zero, though the minimum still defaults to
one.  These shapes are rare and have some odd behavior, but are particularly
important to test for just that reason!

In a related bigfix, :func:`~hypothesis.extra.numpy.arrays` now supports generating
zero-dimensional arrays with `dtype=object` and a strategy for iterable elements.
Previously, the array element would incorrectly be set to the first item in the
generated iterable.

Thanks to Ryan Turner for continuing to improve our Numpy support.
