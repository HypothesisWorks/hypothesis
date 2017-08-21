RELEASE_TYPE: patch

This release fixes two bugs in ``hypothesis.extra.numpy``:

* :func:`~hypothesis.extra.numpy.unicode_string_dtypes` didn't work at all due
  to an incorrect dtype specifier. Now it does.
* Various impossible conditions would have been accepted but would error when
  they fail to produced any example. Now they raise an explicit InvalidArgument
  error.
