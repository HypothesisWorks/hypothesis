RELEASE_TYPE: patch

This patch adds an internal special case to make
:func:`sampled_from(...).filter(...) <hypothesis.strategies.sampled_from>`
much more efficient when the filter rejects most elements (:issue:`1885`).
