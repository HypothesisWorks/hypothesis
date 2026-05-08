RELEASE_TYPE: patch

This patch adds a shrinking pass that tries natural text transformations -
unicode decomposition (NFD/NFKD) and case mapping - on individual
characters in string choices.  Failures involving e.g. ``"À" != "À".lower()``
will now reliably shrink to ``"A"`` rather than sometimes getting stuck on
the high-codepoint accented form (:issue:`4725`).
