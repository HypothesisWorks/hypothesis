RELEASE_TYPE: patch

This patch improves the |Phase.explain| phase so that simple cases like
``assert n1 == n2`` no longer get a misleading ``# or any other generated value``
comment (:issue:`4715`). Before falling back to random sampling, we now also
try the minimal value, the smallest non-minimal value, and values borrowed
from each other arg slice with matching shape.
