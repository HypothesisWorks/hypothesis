RELEASE_TYPE: patch

This patch fixes a significant slowdown when using the :func:`~hypothesis.stateful.precondition` decorator in some cases, due to expensive repr formatting internally (:issue:`3963`).
