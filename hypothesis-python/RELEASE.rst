RELEASE_TYPE: patch

This patch fixes an internal error in :func:`~hypothesis.strategies.datetimes`
with ``allow_imaginary=False`` where the ``timezones`` argument can generate
``tzinfo=None`` (:issue:`2662`).
