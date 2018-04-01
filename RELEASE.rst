RELEASE_TYPE: minor

This release includes several improvements to the handling of the
:obj:`~hypothesis.settings.database` setting.

- The :obj:`~hypothesis.settings.database_file` setting was a historical
  artefact, and you should just use :obj:`~hypothesis.settings.database`
  directly.
- The :envvar:`HYPOTHESIS_DATABASE_FILE` environment variable is
  deprecated, in favor of :meth:`~hypothesis.settings.load_profile` and
  the :obj:`~hypothesis.settings.database` setting.
- If you have not configured the example database at all and the default
  location is not usable (due to e.g. permissions issues), Hypothesis
  will fall back to an in-memory database.  This is not persisted between
  sessions, but means that the defaults work on read-only filesystems.
