RELEASE_TYPE: minor

This release should make the :class:`~hypothesis.settings` feature
easier to use.

- Deprecated settings that no longer have any effect are no longer
  shown in the ``__repr__`` unless set to a non-default value.
- :obj:`~hypothesis.settings.perform_health_check` is deprecated, as it
  duplicates :obj:`~hypothesis.settings.suppress_health_check`.
- :obj:`~hypothesis.settings.max_iterations` is deprecated and disabled,
  because we can usually get better behaviour from an internal heuristic
  than a user-controlled setting.
