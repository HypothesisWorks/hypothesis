RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.stateful.consumes` so that consuming
bundle strategies can be composed with ``.flatmap(...)`` without raising a
``TypeError`` while constructing the strategy (:issue:`4427`).

Thanks to marko1olo for this fix!
