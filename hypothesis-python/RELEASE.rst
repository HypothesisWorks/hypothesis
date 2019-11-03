RELEASE_TYPE: minor

This release adds the strategy :func:`~hypothesis.extra.numpy.mutually_broadcastable_shapes`, which generates multiple array shapes that are mutually broadcast-compatible with an optional user-specified base-shape.

This is a generalisation of :func:`~hypothesis.extra.numpy.broadcastable_shapes`. It relies heavily on non-public internals for performance when generating and shrinking examples. We intend to support generating shapes matching a ufunc signature in a future version.

Thanks to Ryan Soklaski, Zac Dodds, and @rdturnermtl who contributed to this new feature.