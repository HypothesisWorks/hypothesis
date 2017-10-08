RELEASE_TYPE: patch

This release fixes a performance problem in tests where
 :attr:`~hypothesis.settings.use_coverage` is set to True.

Tests experience a slow-down proportionate to the amount of code they cover.
This is still the case, but the factor is now low enough that it should be
unnoticeable. Previously it was large and became much larger in 3.28.4.
