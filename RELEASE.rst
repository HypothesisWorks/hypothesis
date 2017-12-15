RELEASE_TYPE: minor

:exc:`~hypothesis.errors.HypothesisDeprecationWarning` now inherits from
:exc:`python:FutureWarning` instead of :exc:`python:DeprecationWarning`,
as recommended by :pep:`565` for user-facing warnings (:issue:`618`).
If you have not changed the default warnings settings, you will now see
each distinct :exc:`~hypothesis.errors.HypothesisDeprecationWarning`
instead of only the first.
