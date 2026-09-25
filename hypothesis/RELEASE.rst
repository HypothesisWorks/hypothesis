RELEASE_TYPE: patch

This patch makes generating unique collections, such as |st.sets| or
|st.lists| with ``unique=True``, considerably more efficient (:issue:`4458`).
Hypothesis no longer mutates test cases by copying one element of a unique
collection over another element of the same collection, and no longer probes
for minimal examples by drawing every element at its simplest value - both of
which were certain to be rejected, and could waste several times as many
draws from the element strategy as were actually returned.
