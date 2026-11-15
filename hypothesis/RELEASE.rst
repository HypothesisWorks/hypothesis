RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.strategies.sampled_from` of tuples or
frozensets containing strategies. The label of such a strategy depended on
object identity, so ``derandomize=True`` could draw different examples on
each run (:issue:`4958`).

Thanks to rome-xi for this fix!
