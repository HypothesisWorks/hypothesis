RELEASE_TYPE: minor

The :func:`~hypothesis.strategies.functions` strategy has a new argument
``pure=True``, which ensures that the same return value is generated for
identical calls to the generated function (:issue:`2538`).

Thanks to Zac Hatfield-Dodds and Nikita Sobolev for this feature!
