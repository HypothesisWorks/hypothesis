RELEASE_TYPE: patch

This patch improves the performance of shrinking - the process by which
Hypothesis reduces a failing example to a minimal one.  Shrinking large floats
(those above ``2**53``) and shrinking collections such as
:func:`~hypothesis.strategies.lists` are now substantially faster, especially
for large inputs, with no change to the final shrunk result.
