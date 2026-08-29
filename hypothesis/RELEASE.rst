RELEASE_TYPE: patch

This patch fixes the ``redistribute_numeric_pairs`` shrink pass, which
incorrectly checked ``node1.type`` instead of ``node2.type`` when guarding
against float precision loss above ``MAX_PRECISE_INTEGER``.
