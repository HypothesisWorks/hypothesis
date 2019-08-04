RELEASE_TYPE: patch

This patch tidies up the repr of several ``settings``-related objects,
at runtime and in the documentation, and deprecates the undocumented
edge case that ``phases=None`` was treated like ``phases=tuple(Phase)``.

It *also* fixes :func:`~hypothesis.extra.lark.from_lark` with
:pypi:`lark 0.7.2 <lark-parser>` and later.
