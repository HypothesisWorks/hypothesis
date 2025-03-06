RELEASE_TYPE: patch

This patch improves shrinking behavior for values from :func:`~hypothesis.strategies.text` and :func:`~hypothesis.strategies.binary` which contain duplicate elements, like ``"zzzabc"``. It also improves shrinking for  bugs which require the same character to be drawn from two different :func:`~hypothesis.strategies.text` strategies to trigger.
