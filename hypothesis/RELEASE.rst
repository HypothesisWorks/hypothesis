RELEASE_TYPE: patch

This patch fixes a shrinking pass that simultaneously reduces nearby integers
with a fixed relative difference, which previously failed when shrinking
towards a non-zero target (such as year values in
:func:`~hypothesis.strategies.dates` or integers with a non-zero
``shrink_towards``).
