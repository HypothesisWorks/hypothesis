RELEASE_TYPE: patch

This patch makes unique :func:`~hypothesis.extra.numpy.arrays` much more
efficient, especially when there are only a few valid elements - such as
for eight-bit integers (:issue:`3066`).
