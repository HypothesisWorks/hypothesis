RELEASE_TYPE: patch

This patch improves shrinking and generation for collection strategies which
reject some drawn elements, such as :func:`~hypothesis.strategies.lists` with
``unique=True``. Rejected elements are now marked as discarded, so the
shrinker can delete them wholesale and generation avoids revisiting
choices that would be rejected again.
