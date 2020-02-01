RELEASE_TYPE: patch

This patch improves the repr of :func:`~hypothesis.strategies.from_type`,
so that in most cases it will display the strategy it resolves to rather
than ``from_type(...)``.  The latter form will continue to be used where
resolution is not immediately successful, e.g. invalid arguments or
recursive type definitions involving forward references.
