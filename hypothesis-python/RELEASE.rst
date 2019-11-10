RELEASE_TYPE: minor

This release adds a ``gufunc`` argument to
:func:`~hypothesis.extra.numpy.mutually_broadcastable_shapes` (:issue:`2174`),
which allows us to generate shapes which are valid for functions like
:obj:`numpy:numpy.matmul` that require shapes which are not simply broadcastable.

Thanks to everyone who has contributed to this feature over the last year,
and a particular shout-out to Zac Hatfield-Dodds and Ryan Soklaski for
:func:`~hypothesis.extra.numpy.mutually_broadcastable_shapes` and to
Ryan Turner for the downstream :pypi:`hypothesis-gufunc` project.
