RELEASE_TYPE: minor

When a failure found by an :ref:`alternative backend <alternative-backends>` does not reproduce under the Hypothesis backend, we now raise |FlakyBackendFailure| instead of an internal ``FlakyReplay`` exception.
