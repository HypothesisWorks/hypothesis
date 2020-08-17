RELEASE_TYPE: minor

:func:`~hypothesis.strategies.register_type_strategy` no longer accepts
parametrised user-defined generic types, because the resolution logic
was quite badly broken (:issue:`2537`).

Instead of registering a strategy for e.g. ``MyCollection[int]``, you
should register a *function* for ``MyCollection`` and `inspect the type
parameters within that function <https://stackoverflow.com/q/48572831>`__.

Thanks to Nikita Sobolev for the bug report, design assistance, and
pull request to implement this feature!
