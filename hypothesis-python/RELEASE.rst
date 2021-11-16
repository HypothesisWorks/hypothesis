RELEASE_TYPE: patch

This patch makes :func:`hypothesis.strategies.floats` generate
:wikipedia:`"subnormal" floating point numbers <Subnormal_number>`
more often, as these rare values can have strange interactions with
`unsafe compiler optimisations like -ffast-math
<https://simonbyrne.github.io/notes/fastmath/#flushing_subnormals_to_zero>`__
(:issue:`2976`).
