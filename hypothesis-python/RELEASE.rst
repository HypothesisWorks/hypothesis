RELEASE_TYPE: patch

This patch fixes :func:`hypothesis.stateful.consumes` so that values consumed
from bundles can be used with :func:`~hypothesis.strategies.SearchStrategy.flatmap`
without raising a ``TypeError`` (:issue:`4427`).

Thanks to Mirochill for this fix!
