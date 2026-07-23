RELEASE_TYPE: patch

This patch improves our internal ``@proxies`` decorator, which now preserves
the kind of the decorated function: proxies for async functions, generator
functions, and async generator functions are themselves functions of the same
kind.  This prepares for upcoming :func:`~hypothesis.strategies.functions`
support (:issue:`4149`).
