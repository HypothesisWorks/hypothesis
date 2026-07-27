RELEASE_TYPE: minor

The ``codec`` argument to :func:`~hypothesis.strategies.characters` now
excludes characters which do not round-trip: a few legacy codecs have lossy
mappings where encoding succeeds but decoding returns a different character,
for example the yen sign becomes a backslash under ``shift_jis``, so
generated strings could fail encode-decode round-trip tests (:issue:`4813`).
If you want such characters anyway, pass them in ``include_characters``.
