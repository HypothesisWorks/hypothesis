RELEASE_TYPE: patch

This patch takes the previous efficiency improvements to
:func:`sampled_from(...).filter(...) <hypothesis.strategies.sampled_from>`
strategies that reject most elements, and generalises them to also apply to
``sampled_from(...).filter(...).filter(...)`` and longer chains of filters.
