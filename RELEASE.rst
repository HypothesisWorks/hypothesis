RELEASE_TYPE: minor

This release deprecates passing ``elements=None`` to collection strategies,
such as :func:`~hypothesis.strategies.lists`.

Requiring ``lists(nothing())`` or ``builds(list)`` instead of ``lists()``
means slightly more typing, but also improves the consistency and
discoverability of our API - as well as showing how to compose or
construct strategies in ways that still work in more complex situations.

Passing a nonzero max_size to a collection strategy where the elements
strategy contains no values is now deprecated, and will be an error in a
future version.  The equivalent with ``elements=None`` is already an error.
