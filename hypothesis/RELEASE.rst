RELEASE_TYPE: patch

This patch fixes three cases where :ref:`the Ghostwriter <ghostwriter>` wrote
tests that could not run:

- On Python 3.14, the repr of :func:`~hypothesis.strategies.from_type` for a
  union such as ``MyClass | None`` no longer gains a spurious ``typing.`` prefix.
- Class methods, such as ``st.text().map(MyClass.parse)``, are now shown with
  their class name.
- Tests for collections of values which cannot be hashed, such as
  ``Iterable[tuple[list[int]]]``, no longer raise an error.

Thanks to ZacKienzle2 for this fix!
