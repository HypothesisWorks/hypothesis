RELEASE_TYPE: patch

If the :obj:`~hypothesis.Phase.shrink` phase is disabled, we now stop the
:obj:`~hypothesis.Phase.generate` phase as soon as an error is found regardless
of the value of the ``report_multiple_examples`` setting, since that's
probably what you wanted (:issue:`3244`).
