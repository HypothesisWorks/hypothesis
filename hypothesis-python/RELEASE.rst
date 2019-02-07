RELEASE_TYPE: patch

Fixes bug in `hypothesis.extra.numpy.arrays` on Python2 where `long` type
dimensions are not allowed in the shape.
