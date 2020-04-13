RELEASE_TYPE: minor

Failing tests which use :func:`~hypothesis.target` now report the highest
score observed for each target alongside the failing example(s), even without
:ref:`explicitly showing test statistics <statistics>`.

This improves the debugging workflow for tests of accuracy, which assert that the
total imprecision is within some error budget - for example, ``abs(a - b) < 0.5``.
Previously, shrinking to a minimal failing example could often make errors seem
smaller or more subtle than they really are (see `the threshold problem
<https://hypothesis.works/articles/threshold-problem/>`__, and :issue:`2180`).
