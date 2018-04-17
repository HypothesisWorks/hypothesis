RELEASE_TYPE: minor

This release deprecates several redundant or internally oriented
:class:`~hypothesis.settings`, working towards an orthogonal set of
configuration options that are widely useful *without* requiring any
knowledge of our internals (:issue:`535`).

- Deprecated settings that no longer have any effect are no longer
  shown in the ``__repr__`` unless set to a non-default value.
- :obj:`~hypothesis.settings.perform_health_check` is deprecated, as it
  duplicates :obj:`~hypothesis.settings.suppress_health_check`.
- :obj:`~hypothesis.settings.max_iterations` is deprecated and disabled,
  because we can usually get better behaviour from an internal heuristic
  than a user-controlled setting.
- :obj:`~hypothesis.settings.min_satisfying_examples` is deprecated and
  disabled, due to overlap with the
  :obj:`~hypothesis.settings.HealthCheck.filter_too_much` healthcheck
  and poor interaction with :obj:`~hypothesis.settings.max_examples`.
- :envvar:`HYPOTHESIS_VERBOSITY_LEVEL` was never documented, but is
  now explicitly deprecated.  Set :obj:`~hypothesis.settings.verbosity`
  through the profile system instead.
- Examples tried by :func:`~hypothesis.find` are now reported at ``debug``
  verbosity level (as well as ``verbose`` level).
