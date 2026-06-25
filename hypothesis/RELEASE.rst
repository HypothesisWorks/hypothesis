RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.stateful.consumes` so it can be combined
with ``.flatmap()`` without raising a ``TypeError`` (:issue:`4427`).

Thanks to gaoflow for this fix!
