RELEASE_TYPE: minor

This release adds a setting to the public API, and does some internal cleanup:

- The :attr:`~hypothesis.settings.derandomize` setting is now documented (:issue:`890`)
- Removed - and disallowed - all 'bare excepts' in Hypothesis (:issue:`953`)
- Documented the :attr:`~hypothesis.settings.strict` setting as deprecated, and
  updated the build so our docs always match deprecations in the code.
