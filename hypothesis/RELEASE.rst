RELEASE_TYPE: patch

This patch fixes a bug where shrinking a failing example from
:func:`~hypothesis.strategies.one_of` of text strategies with different
alphabets could crash with ``ValueError: <n> is not in list`` instead of
reporting the minimal failing example (:issue:`4905`).
