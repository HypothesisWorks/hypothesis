RELEASE_TYPE: minor

This release deprecates passing ``elements=None`` to collection strategies,
such as :func:`~hypothesis.strategies.lists`.

Requiring ``lists(nothing())`` or ``builds(list)`` instead of ``lists()``
means slightly more typing, but also improves the consistency and
discoverability of our API - as well as showing how to compose or
construct strategies in ways that still work in more complex situations.
