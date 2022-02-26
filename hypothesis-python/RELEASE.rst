RELEASE_TYPE: minor

This release makes :func:`~hypothesis.strategies.floats` error *consistently* when
your floating-point hardware has been configured to violate IEEE-754 for
:wikipedia:`subnormal numbers <Subnormal_number>`, instead of
only when an internal assertion was tripped (:issue:`3092`).

If this happens to you, passing ``allow_subnormal=False`` will suppress the explicit
error.  However, we strongly recommend fixing the root cause by disabling global-effect
unsafe-math compiler options instead, or at least consulting e.g. Simon Byrne's
`Beware of fast-math <https://simonbyrne.github.io/notes/fastmath/>`__ explainer first.
