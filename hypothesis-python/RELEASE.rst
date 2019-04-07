RELEASE_TYPE: patch

This release fixes a bug introduced in :ref:`Hypothesis 4.14.3 <v4.14.3>`
that would sometimes cause
:func:`sampled_from(...).filter(...) <hypothesis.strategies.sampled_from>`
to encounter an internal assertion failure when there are three or fewer
elements, and every element is rejected by the filter.
