RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.strategies.functions` for inspectable
callables such as :func:`functools.partial`, classes, and callable instances
(:issue:`4950`).
For these newly supported prototypes, generated functions retain the known
interpretation context of copied annotations when used with :func:`~hypothesis.strategies.functions`
or :func:`~hypothesis.strategies.builds`.

Thanks to Justin Guida for this bug fix!
