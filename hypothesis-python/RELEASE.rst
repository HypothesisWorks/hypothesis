RELEASE_TYPE: minor

This release deprecates the use of :class:`~hypothesis.settings` as a
context manager, the use of which is somewhat ambiguous.

Users should define settings with global state or with the
:func:`@settings(...) <hypothesis.settings>` decorator.
