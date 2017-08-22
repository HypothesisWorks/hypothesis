RELEASE_TYPE: minor

This fixes a bug in `hypothesis.extra.numpy` where an invalid endianness
argument would fail with an internal error instead of an InvalidArgument
exception.
