RELEASE_TYPE: minor

This release changes some inconsistent behavior of :func:`~hypothesis.extra.numpy.arrays`
from the Numpy extra when asked for an array of ``shape=()``.
:func:`~hypothesis.extra.numpy.arrays` will now always return a Numpy
:class:`~numpy:numpy.ndarray`, and the array will always be of the requested dtype.

Thanks to Ryan Turner for this change.
