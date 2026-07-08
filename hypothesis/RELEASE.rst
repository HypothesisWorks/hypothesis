RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.stateful.consumes` so that consumed bundles
can be used with ``.flatmap()`` in stateful rules (:issue:`4427`).

Thanks to ychampion for this fix!
