RELEASE_TYPE: minor

The ``alphabet`` argument for :func:`~hypothesis.strategies.text` now
uses its default value of ``characters(blacklist_categories=('Cs',))``
directly, instead of hiding that behind ``alphabet=None`` and replacing
it within the function.  Passing ``None`` is therefore deprecated.
