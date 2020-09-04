RELEASE_TYPE: patch

This patch makes the :doc:`ghostwriter <ghostwriter>` much more robust when
passed unusual modules.

- improved support for non-resolvable type annotations
- :func:`~hypothesis.extra.ghostwriter.magic` can now write
  :func:`~hypothesis.extra.ghostwriter.equivalent` tests
- running :func:`~hypothesis.extra.ghostwriter.magic` on modules where some
  names in ``__all__`` are undefined skips such names, instead of raising an error
- :func:`~hypothesis.extra.ghostwriter.magic` now knows to skip mocks
- improved handling of import-time errors found by the ghostwriter CLI
