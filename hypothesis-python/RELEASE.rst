RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.stateful.consumes` when combined with
|.flatmap|, which previously raised a ``TypeError`` before the
state machine could run (:issue:`4427`).

Thanks to Sean Kenneth Doherty for this fix!
